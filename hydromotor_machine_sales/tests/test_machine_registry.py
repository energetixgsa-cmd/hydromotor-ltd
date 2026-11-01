"""REAL Odoo/PostgreSQL tests, NOT executed locally (Odoo unavailable).

Disposable staging test DB only. TransactionCase fixtures are rolled back;
no commits, no external service calls. Separate two-worker race acceptance
is still required; a unique-index test is not a concurrent request test.
"""
from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'hm_machine_registry')
class TestMachineRegistry(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'HM FIXTURE Registry Customer'})
        self.product = self.env['product.product'].create({
            'name': 'HM FIXTURE Serialized Machine', 'type': 'consu',
            'is_storable': True, 'tracking': 'serial', 'x_hm_is_machine': True,
        })
        self.base = self.env['x_hm_base'].create({
            'x_name': 'HM FIXTURE 42-5 .16 H', 'x_code': 'HM_REGISTRY_FIXTURE',
            'x_version': 'FIXTURE', 'x_family': '42-5', 'x_price': 1000,
            'x_product_id': self.product.id,
        })
        self.product.x_hm_base_id = self.base
        eur = self.env.ref('base.EUR')
        pricelist = self.env['product.pricelist'].create({
            'name': 'HM FIXTURE EUR', 'currency_id': eur.id,
        })
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id, 'pricelist_id': pricelist.id,
            'company_id': self.env.company.id,
        })
        self.config = self.env['x_hm_config'].create({
            'x_name': 'HM FIXTURE Registry Configuration',
            'x_company_id': self.env.company.id, 'x_partner_id': self.partner.id,
            'x_order_id': self.order.id, 'x_base_id': self.base.id,
            'x_quantity': 2, 'x_market': 'EU', 'x_chassis_type': 'unspecified', 'x_language': 'bg',
        })
        settings = self.env['x_hm_settings'].search([('x_company_id', '=', self.env.company.id)])
        self.assertEqual(len(settings), 1, 'Test DB requires exactly one native registry setting')
        settings.write({'x_enabled': True, 'x_target_model_id': self.env.ref('hydromotor_service.model_machine').id})
        self._run('hydromotor_machine_sales.publish_config', self.config)
        self.line = self.order.order_line.filtered('x_hm_config_id')
        self.registry = self.env['hydromotor.machine.registry']

    def _run(self, xmlid, records):
        return self.env.ref(xmlid).with_context(
            active_model=records._name, active_ids=records.ids, active_id=records[0].id,
        ).run()

    def _machines(self):
        return self.env['x_hm_machine'].search([('x_sale_order_id', '=', self.order.id)], order='id')

    def test_confirmation_and_cancel_reconfirm_replay(self):
        self.order.action_confirm()
        machines = self._machines()
        self.assertEqual(len(machines), 2)
        self.assertFalse(machines.mapped('x_lot_id'))
        self.assertFalse(any(machines.mapped('x_identity_key')))
        self.assertFalse(machines.mapped('x_product_id'))  # related only to real lot
        self._run('hydromotor_machine_sales.sync_sale_manual', self.order)
        self.assertEqual(self._machines(), machines)
        self.order._action_cancel()
        self.assertEqual(set(machines.mapped('x_hms_order_state')), {'cancel'})
        self.order.action_draft()
        self.order.action_confirm()
        self.assertEqual(self._machines(), machines)
        self.assertEqual(set(machines.mapped('x_hms_order_state')), {'sale'})

    def test_stock_completion_and_manual_registration_keep_same_dossiers(self):
        self.order.action_confirm()
        machines = self._machines()
        picking = self.order.picking_ids.filtered(lambda p: p.location_dest_id.usage == 'customer')
        self.assertEqual(len(picking), 1)
        lots = self.env['stock.lot']
        for number in range(2):
            lot = self.env['stock.lot'].create({
                'name': '000-HM-FIXTURE-%s' % number, 'product_id': self.product.id,
                'company_id': self.env.company.id,
            })
            lots |= lot
            self.env['stock.quant']._update_available_quantity(self.product, picking.location_id, 1, lot_id=lot)
        picking.action_assign()
        self.assertEqual(len(picking.move_line_ids), 2)
        picking.move_line_ids.write({'quantity': 1, 'picked': True})
        picking._action_done()  # standard core completion followed by our hook
        self.assertEqual(self._machines(), machines)
        self.assertEqual(machines.mapped('x_lot_id'), lots)
        self.assertEqual(set(machines.mapped('x_identity_key')),
                         {'%s/%s' % (self.env.company.id, lot.id) for lot in lots})
        self.assertEqual(machines.mapped('x_product_id'), self.product)
        self._run('hydromotor_service.action_register_sale', self.order)
        self._run('hydromotor_service.action_register_sale', self.order)
        self.assertEqual(self._machines(), machines)

    def test_unique_source_is_enforced_by_postgres_not_search_then_create(self):
        self.order.action_confirm()
        machine = self._machines()[0]
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['x_hm_machine'].create({
                'x_name': 'HM FIXTURE duplicate must fail',
                'x_company_id': self.env.company.id, 'x_partner_id': self.partner.id,
                'x_sale_order_id': self.order.id, 'x_hms_source_key': machine.x_hms_source_key,
            })
            self.env.flush_all()

    def test_registry_hook_can_be_replayed_without_duplicate_indexes(self):
        self.registry._register_hook()
        self.registry._register_hook()
        self.env.cr.execute("SELECT indexname FROM pg_indexes WHERE indexname IN %s", [(
            'hm_bridge_source_unique', 'hm_machine_source_unique', 'hm_machine_company_lot_unique')])
        self.assertEqual(len(self.env.cr.fetchall()), 3)
