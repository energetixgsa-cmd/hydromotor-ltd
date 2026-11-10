from odoo.tests import Form, TransactionCase, tagged
from lxml import etree
from odoo.exceptions import AccessError, ValidationError, UserError
import unittest
from odoo.tests.common import new_test_user




@tagged('post_install', '-at_install', 'hm_site_plant')
class TestSitePlant(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Local fixture owner'})
        cls.project = cls.env['project.project'].create({'name': 'Local site A', 'company_id': cls.env.company.id})
        cls.other_site = cls.env['project.project'].create({'name': 'Local site B', 'company_id': cls.env.company.id})
        cls.plant = cls.env['hm.concrete.plant'].create({'name': 'Local plant', 'project_id': cls.project.id})
        cls.product = cls.env['product.product'].create({'name': 'Local serial machine', 'is_storable': True, 'tracking': 'serial'})
        lot = cls.env['stock.lot'].create({'name': 'LOCAL-0001', 'product_id': cls.product.id, 'company_id': cls.env.company.id})
        cls.machine = cls.env['x_hm_machine'].create({'x_name': 'Local machine', 'x_lot_id': lot.id, 'x_partner_id': cls.partner.id, 'x_company_id': cls.env.company.id})

    def test_05_existing_machine_company_guard_is_preserved(self):
        self.env['hm.machine.assignment'].create({'machine_id': self.machine.id, 'project_id': self.project.id})
        other = self.env['res.company'].create({'name': 'Local company mutation'})
        with self.assertRaises(UserError), self.cr.savepoint():
            self.machine.x_company_id = other
            self.machine.flush_recordset(['x_company_id'])

    def test_06_restricted_roles_and_companies(self):
        service = new_test_user(self.env(context=dict(self.env.context, no_reset_password=True)), login='local_site_service', groups='hydromotor_service.group_service_user,project.group_project_user')
        sales = new_test_user(self.env(context=dict(self.env.context, no_reset_password=True)), login='local_site_sales', groups='sales_team.group_sale_salesman,project.group_project_user')
        nobody = new_test_user(self.env(context=dict(self.env.context, no_reset_password=True)), login='local_site_nobody', groups='base.group_user')
        vals = {'machine_id': self.machine.id, 'project_id': self.project.id}
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.env['hm.machine.assignment'].with_user(sales).create(vals)
        record = self.env['hm.machine.assignment'].with_user(service).create(vals)
        self.assertEqual(record.create_uid, service)
        with self.assertRaises(AccessError), self.cr.savepoint():
            record.with_user(sales).action_end()
        with self.assertRaises(AccessError), self.cr.savepoint():
            record.with_user(nobody).read(['project_id'])
        foreign = self.env['res.company'].create({'name': 'Restricted foreign company'})
        foreign_site = self.env['project.project'].with_company(foreign).create({'name': 'Invisible site', 'company_id': foreign.id})
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.env['hm.machine.assignment'].with_user(service).create({**vals, 'project_id': foreign_site.id})
        record.with_user(service).action_end()

    def test_12_batch_replay_retains_input_cardinality(self):
        vals = {'machine_id': self.machine.id, 'project_id': self.project.id, 'request_key': 'batch-replay'}
        records = self.env['hm.machine.assignment'].create([vals, vals])
        self.assertEqual(len(records), 2, 'Batch RPC results must map one-to-one to input commands')
        self.assertEqual(records[0], records[1])
        self.assertEqual(len(self.machine.x_hm_assignment_ids), 1)

    def test_11_failed_command_is_atomic_even_when_caller_catches(self):
        ledger = self.env['hm.machine.assignment']
        record = ledger.create({'machine_id': self.machine.id, 'project_id': self.project.id})
        with unittest.TestCase.assertRaises(self, ValueError):
            ledger.create({'machine_id': self.machine.id, 'project_id': self.other_site.id, 'unknown_payload_field': 'reject'})
        record.invalidate_recordset(['ended_at'])
        self.assertFalse(record.ended_at, 'Failed assignment command closed the current assignment')
        self.assertEqual(self.machine.x_hm_site_id, self.project)

    def test_10_sales_web_save_echo_company_and_confirm_remain_planned(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id, 'hm_target_project_id': self.project.id})
        line = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id})
        order.web_save({'hm_target_project_id': self.other_site.id, 'order_line': [[1, line.id, {'hm_target_project_id': self.other_site.id}]]}, specification={})
        self.assertTrue(line.hm_use_order_target)
        self.assertEqual(line.hm_target_project_id, self.other_site)
        foreign = self.env['res.company'].create({'name': 'Foreign sales company'})
        site = self.env['project.project'].with_company(foreign).create({'name': 'Foreign sales site', 'company_id': foreign.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.hm_target_project_id = site
        with self.assertRaises(ValidationError), self.cr.savepoint():
            line.hm_target_project_id = site
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['sale.order.line'].create({'order_id': order.id, 'display_type': 'line_note', 'name': 'Note', 'hm_target_project_id': self.project.id})
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertFalse(self.machine.x_hm_assignment_ids)
        self.assertFalse(self.env['hm.machine.assignment'].search([('project_id', 'in', [self.project.id, self.other_site.id])]))

    def test_09_editable_forms_and_reverse_views(self):
        view = self.env.ref('hydromotor_site_plant.assignment_form', raise_if_not_found=False)
        self.assertTrue(view, 'Editable assignment UI is missing')
        with Form(self.env['hm.machine.assignment'], view=view.id) as form:
            form.machine_id = self.machine
            form.project_id = self.project
            form.plant_id = self.plant
        self.assertEqual(form.record.machine_id, self.machine)
        machine_arch = etree.fromstring(self.env['x_hm_machine'].get_view(view_id=self.env.ref('hydromotor_service.machine_form').id)['arch'])
        self.assertTrue(machine_arch.xpath("//field[@name='x_hm_assignment_ids']"))
        with Form(self.env['sale.order']) as order_form:
            order_form.partner_id = self.partner
            order_form.hm_target_project_id = self.project
            order_form.hm_target_plant_id = self.plant
            with order_form.order_line.new() as line:
                line.product_id = self.product
        order = order_form.record
        self.assertEqual(order.order_line.hm_target_project_id, self.project)
        self.assertEqual(order.order_line.hm_target_plant_id, self.plant)
        with Form(order) as edit:
            edit.hm_target_project_id = self.other_site
        self.assertFalse(order.hm_target_plant_id)
        self.assertTrue(order.order_line.hm_use_order_target)
        self.assertEqual(order.order_line.hm_target_project_id, self.other_site)
        for model, xid in [('project.project', 'project.edit_project'), ('sale.order', 'sale.view_order_form')]:
            arch = etree.fromstring(self.env[model].get_view(view_id=self.env.ref(xid).id)['arch'])
            expected = 'hm_assignment_ids' if model == 'project.project' else 'hm_target_project_id'
            self.assertTrue(arch.xpath("//field[@name='%s']" % expected))

    def test_08_database_company_and_site_foreign_keys(self):
        self.cr.execute("SELECT conname FROM pg_constraint WHERE conname LIKE 'hm_site_scope_%'")
        self.assertEqual(len(self.cr.fetchall()), 7, 'Composite company/site integrity constraints are missing')

    def test_07_planned_plant_cannot_be_reparented(self):
        self.env['sale.order'].create({'partner_id': self.partner.id, 'hm_target_project_id': self.project.id, 'hm_target_plant_id': self.plant.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.plant.project_id = self.other_site
            self.plant.flush_recordset(['project_id'])

    def test_04_sales_targets_are_planned_with_line_override_and_clear(self):
        self.assertIn('hm_target_project_id', self.env['sale.order']._fields, 'Planned quotation target is missing')
        order = self.env['sale.order'].create({'partner_id': self.partner.id, 'hm_target_project_id': self.project.id, 'hm_target_plant_id': self.plant.id})
        line = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id})
        override = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id, 'hm_target_project_id': self.other_site.id})
        cleared = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id, 'hm_target_project_id': False})
        self.assertEqual(line.hm_target_project_id, self.project)
        self.assertEqual(line.hm_target_plant_id, self.plant)
        self.assertFalse(override.hm_use_order_target)
        self.assertFalse(cleared.hm_use_order_target)
        order.write({'hm_target_project_id': self.other_site.id, 'hm_target_plant_id': False})
        self.assertEqual(line.hm_target_project_id, self.other_site)
        self.assertEqual(override.hm_target_project_id, self.other_site)
        self.assertFalse(cleared.hm_target_project_id)
        line.write({'hm_target_project_id': False, 'hm_target_plant_id': False})
        self.assertFalse(line.hm_use_order_target)
        line.hm_use_order_target = True
        self.assertEqual(line.hm_target_project_id, self.other_site)
        self.assertFalse(order.copy().hm_target_project_id)
        self.assertFalse(order.copy().order_line.hm_target_project_id)
        self.assertFalse(self.machine.x_hm_assignment_ids, 'Offering equipment is not installation')
        self.assertFalse(order.x_hm_machine_ids, 'Sold machines must stay a separate relation')
        self.assertFalse(line.x_hm_parts_machine_id, 'Parts target must stay a separate relation')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.write({'hm_target_plant_id': self.plant.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            override.write({'hm_target_plant_id': self.plant.id})

    def test_03_company_site_plant_and_timestamp_validation(self):
        ledger = self.env['hm.machine.assignment']
        with self.assertRaises(ValidationError), self.cr.savepoint():
            ledger.create({'machine_id': self.machine.id, 'project_id': self.other_site.id, 'plant_id': self.plant.id})
        other = self.env['res.company'].create({'name': 'Local other company'})
        foreign_site = self.env['project.project'].with_company(other).create({'name': 'Foreign site', 'company_id': other.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            ledger.create({'machine_id': self.machine.id, 'project_id': foreign_site.id, 'company_id': other.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            ledger.create({'machine_id': self.machine.id, 'project_id': self.project.id, 'started_at': '2020-01-01'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['hm.concrete.plant'].create({'name': 'Wrong company', 'project_id': foreign_site.id})
        assignment = ledger.create({'machine_id': self.machine.id, 'project_id': self.project.id, 'plant_id': self.plant.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.plant.project_id = self.other_site
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.project.company_id = other
        assignment.action_end()

    def test_02_move_replay_close_and_immutable_history(self):
        ledger = self.env['hm.machine.assignment']
        self.assertIn('request_key', ledger._fields, 'Replay-safe assignment command is missing')
        first = ledger.create({'machine_id': self.machine.id, 'project_id': self.project.id, 'plant_id': self.plant.id, 'request_key': 'first'})
        second = ledger.create({'machine_id': self.machine.id, 'project_id': self.other_site.id, 'request_key': 'second'})
        self.assertEqual(first.ended_at, second.started_at)
        self.assertEqual(self.machine.x_hm_site_id, self.other_site)
        self.assertEqual(ledger.create({'machine_id': self.machine.id, 'project_id': self.project.id, 'plant_id': self.plant.id, 'request_key': 'first'}), first)
        self.assertEqual(self.machine.x_hm_site_id, self.other_site)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            first.write({'ended_at': False})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            first.unlink()
        second.action_end()
        second.action_end()
        self.assertFalse(self.machine.x_hm_site_id)
        self.assertEqual(len(self.machine.x_hm_assignment_ids), 2)

    def test_01_assignment_roundtrip_preserves_owner(self):
        self.assertIn('hm.machine.assignment', self.env.registry,
                      'Actual site assignment ledger is not implemented')
        partner, project, plant, machine = self.partner, self.project, self.plant, self.machine
        assignment = self.env['hm.machine.assignment'].create({'machine_id': machine.id, 'project_id': project.id, 'plant_id': plant.id})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(machine.x_hm_site_id, project)
        self.assertEqual(machine.x_hm_plant_id, plant)
        self.assertEqual(machine.x_partner_id, partner)
        self.assertEqual(machine.x_hm_assignment_ids, assignment)


    def test_13_site_entry_form_defaults_and_independent_owner(self):
        from odoo.tools.safe_eval import safe_eval
        action = self.env.ref('hydromotor_site_plant.site_action', raise_if_not_found=False)
        self.assertTrue(action, 'Dedicated site entry action is missing')
        context = safe_eval(action.context, {'allowed_company_ids': [self.env.company.id], 'uid': self.env.uid})
        with Form(self.env['project.project'].with_context(**context), view='hydromotor_site_plant.site_form') as form:
            form.name = 'Local site creation regression'
        site = form.record
        self.assertEqual(site.company_id, self.env.company)
        owner = self.env['res.partner'].create({'name': 'Independent plant owner'})
        with Form(self.env['hm.concrete.plant'], view='hydromotor_site_plant.plant_form') as form:
            form.name = 'Local owned plant'
            form.project_id = site
            form.owner_id = owner
        self.assertEqual(form.record.owner_id, owner)
        self.assertFalse(site.partner_id)
        shared = self.env['project.project'].create({'name': 'Shared not a site', 'company_id': False})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['hm.concrete.plant'].create({'name': 'Rejected shared site', 'project_id': shared.id})
