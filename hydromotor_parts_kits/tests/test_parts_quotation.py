from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestPartsQuotation(TransactionCase):
    """Run on Odoo 19.0 after installing/upgrading this module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = cls.env.user
        groups_field = 'group_ids' if 'group_ids' in user._fields else 'groups_id'
        user.write({groups_field: [(4, cls.env.ref(xmlid).id) for xmlid in (
            'hydromotor_service.group_service_user', 'sales_team.group_sale_salesman',
        )]})
        cls.service = cls.env['hydromotor.parts.quotation.service']
        cls.partner = cls.env['res.partner'].create({'name': 'Тест клиент за части'})
        cls.part = cls.env['product.product'].create({
            'name': 'Тест част', 'default_code': 'HM-TEST-PART',
            'list_price': 120.0, 'sale_ok': True, 'type': 'consu',
        })
        cls.assembly = cls.env['product.product'].create({
            'name': 'Тест възел', 'default_code': '032247006',
            'list_price': 500.0, 'sale_ok': True, 'type': 'consu',
        })
        machine_product = cls.env['product.product'].create({
            'name': 'Тест машина', 'type': 'consu', 'is_storable': True,
            'tracking': 'serial',
        })
        lot = cls.env['stock.lot'].create({
            'name': 'HM-TEST-MACHINE', 'product_id': machine_product.id,
            'company_id': cls.env.company.id,
        })
        cls.machine = cls.env['x_hm_machine'].create({
            'x_name': 'Тест машина / HM-TEST-MACHINE',
            'x_company_id': cls.env.company.id, 'x_partner_id': cls.partner.id,
            'x_lot_id': lot.id,
        })
        cls.kit = cls.env['x_hm_parts_kit'].create({
            'x_name': 'Тест комплект', 'x_company_id': cls.env.company.id,
            'x_active': True, 'x_note': 'Възел 032247006, чертеж 001-01.',
            'x_assembly_product_id': cls.assembly.id,
            'x_line_ids': [(0, 0, {'x_product_id': cls.part.id, 'x_qty': 2})],
        })
        cls.machine.write({'x_parts_kit_ids': [(4, cls.kit.id)]})

    def _wizard(self, mode='parts'):
        action = self.service.action_start_kit(self.kit.id, mode)
        return self.env[action['res_model']].browse(action['res_id'])

    def test_navigation_uses_existing_relation(self):
        self.assertIn(self.machine, self.kit.x_machine_ids)
        action = self.service.action_machine_kits(self.machine.id)
        self.assertEqual(action['domain'], [('id', 'in', self.kit.ids)])

    def test_parts_selection_and_repeated_submit(self):
        wizard = self._wizard()
        wizard.x_line_ids.write({'x_selected': True, 'x_qty': 3})
        action = self.service.action_apply(wizard.id)
        order = self.env['sale.order'].browse(action['res_id'])
        self.assertEqual(order.partner_id, self.partner)
        lines = order.order_line.filtered('product_id')
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_id, self.part)
        self.assertEqual(lines.product_uom_qty, 3)
        self.assertEqual(lines.x_hm_parts_machine_id, self.machine)
        self.assertEqual(lines.x_hm_parts_kit_id, self.kit)
        self.assertEqual(self.service.action_apply(wizard.id)['res_id'], order.id)
        self.assertEqual(len(order.order_line.filtered('product_id')), 1)

    def test_assembly_single_product(self):
        wizard = self._wizard('assembly')
        action = self.service.action_apply(wizard.id)
        lines = self.env['sale.order'].browse(action['res_id']).order_line.filtered('product_id')
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_id, self.assembly)
        self.assertFalse(lines.x_hm_kit_source_line_id)

    def test_single_part_shortcut(self):
        action = self.service.action_start_line(self.kit.x_line_ids.id)
        wizard = self.env[action['res_model']].browse(action['res_id'])
        self.assertEqual(wizard.x_line_ids.filtered('x_selected').x_product_id, self.part)

    def test_empty_selection(self):
        wizard = self._wizard()
        with self.assertRaises(UserError):
            self.service.action_apply(wizard.id)

    def test_link_removed_while_wizard_open(self):
        wizard = self._wizard()
        wizard.x_line_ids.write({'x_selected': True})
        self.machine.write({'x_parts_kit_ids': [(3, self.kit.id)]})
        with self.assertRaises(UserError):
            self.service.action_apply(wizard.id)

    def test_append_keeps_existing_quote_lines(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        original = self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': self.part.id, 'product_uom_qty': 7,
        })
        wizard = self._wizard()
        wizard.write({'x_sale_order_id': order.id})
        wizard.x_line_ids.write({'x_selected': True})
        self.service.action_apply(wizard.id)
        self.assertTrue(original.exists())
        self.assertEqual(original.product_uom_qty, 7)
        self.assertEqual(len(order.order_line.filtered('product_id')), 2)

    def test_assembly_code_must_match(self):
        wizard = self._wizard('assembly')
        wizard.write({'x_assembly_product_id': self.part.id})
        with self.assertRaises(UserError):
            self.service.action_apply(wizard.id)
