"""Odoo 19.0 integration checks; not executed in the preparation environment.

Use only through the Odoo test runner on a disposable development database.
TransactionCase isolates test records and rolls them back after testing.
"""
from datetime import timedelta

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHydromotorService19(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'HM 19.0 TEST - Fictional Customer', 'is_company': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'HM 19.0 TEST - Machine', 'type': 'consu',
            'is_storable': True, 'tracking': 'serial', 'x_hm_is_machine': True,
        })
        cls.lot = cls.env['stock.lot'].create({
            'name': 'HM-19-TEST-0001', 'product_id': cls.product.id,
            'company_id': cls.company.id,
        })
        cls.machine = cls.env['x_hm_machine'].create({
            'x_name': 'HM 19.0 TEST - Dossier', 'x_company_id': cls.company.id,
            'x_partner_id': cls.partner.id, 'x_lot_id': cls.lot.id,
        })
        cls.employee = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'HM 19.0 TEST - Service Employee',
            'login': 'hm_19_test_service_employee',
            'company_id': cls.company.id, 'company_ids': [Command.set([cls.company.id])],
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('hydromotor_service.group_service_user').id,
            ])],
        })

    def _run(self, action, records):
        return self.env.ref('hydromotor_service.' + action).with_context(
            active_model=records._name, active_ids=records.ids,
            active_id=records[0].id if records else False,
        ).run()

    def test_01_security_metadata(self):
        for kind in ['machine', 'job', 'plan', 'meter']:
            rule = self.env.ref('hydromotor_service.access_' + kind + '_company')
            self.assertEqual(rule._name, 'ir.rule')
            self.assertFalse(rule.groups)
            self.assertEqual(rule.domain_force, "[('x_company_id', 'in', company_ids)]")
            employee = self.env.ref('hydromotor_service.access_' + kind + '_user')
            manager = self.env.ref('hydromotor_service.access_' + kind + '_manager')
            self.assertEqual(employee._name, 'ir.model.access')
            self.assertTrue(employee.perm_read and employee.perm_write and employee.perm_create)
            self.assertFalse(employee.perm_unlink)
            self.assertTrue(manager.perm_unlink)

    def test_02_actual_employee_and_public_acl(self):
        for model in ['x_hm_machine', 'x_hm_job', 'x_hm_plan', 'x_hm_meter']:
            acl = self.env['ir.model.access'].with_user(self.employee)
            for operation in ['read', 'write', 'create']:
                self.assertTrue(acl.check(model, operation, raise_exception=False))
            self.assertFalse(acl.check(model, 'unlink', raise_exception=False))
            public_acl = self.env['ir.model.access'].with_user(self.env.ref('base.public_user'))
            self.assertFalse(public_acl.check(model, 'read', raise_exception=False))

    def test_03_machine_identity_and_serial(self):
        self.assertEqual(self.machine.x_identity_key, '%s/%s' % (self.company.id, self.lot.id))
        self.assertEqual(self.machine.x_product_id, self.product)
        self.assertEqual(self.machine.x_serial, self.lot.name)
        visible = self.env['x_hm_machine'].with_user(self.employee).with_context(
            allowed_company_ids=[self.company.id],
        ).search([('id', '=', self.machine.id)])
        self.assertEqual(visible.ids, self.machine.ids)

    def test_04_company_isolation(self):
        other = self.env['res.company'].create({'name': 'HM 19.0 TEST - Other Company'})
        other_lot = self.env['stock.lot'].sudo().create({
            'name': 'HM-19-TEST-OTHER', 'product_id': self.product.id, 'company_id': other.id,
        })
        other_machine = self.env['x_hm_machine'].sudo().with_company(other).create({
            'x_name': 'HM 19.0 TEST - Other Dossier', 'x_company_id': other.id,
            'x_partner_id': self.partner.id, 'x_lot_id': other_lot.id,
        })
        visible = self.env['x_hm_machine'].with_user(self.employee).with_context(
            allowed_company_ids=[self.company.id],
        ).search([('id', '=', other_machine.id)])
        self.assertFalse(visible)

    def test_05_meter_compute(self):
        today = fields.Date.today()
        self.env['x_hm_meter'].create({
            'x_name': 'HM 19.0 TEST - Reading', 'x_machine_id': self.machine.id,
            'x_date': today, 'x_hours': 123.0,
        })
        self.assertEqual(self.machine.x_hours, 123.0)
        self.assertEqual(self.machine.x_last_meter_date, today)

    def test_06_plan_job_idempotence_and_completion(self):
        today = fields.Date.today()
        plan = self.env['x_hm_plan'].create({
            'x_name': 'HM 19.0 TEST - Maintenance Plan', 'x_machine_id': self.machine.id,
            'x_technician_id': self.env.uid, 'x_enabled': True,
            'x_interval_days': 30, 'x_next_date': today,
        })
        self.assertTrue(plan.x_due)
        self._run('action_plan_job', plan)
        self._run('action_plan_job', plan)
        jobs = self.env['x_hm_job'].search([('x_plan_id', '=', plan.id)])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.x_partner_id, self.partner)
        self.assertTrue(jobs.x_reference)
        jobs.write({'x_work_done': 'Fictional acceptance-test work.',
                    'x_coverage': 'charge', 'x_has_meter': True, 'x_meter_hours': 100.0})
        self._run('action_job_done', jobs)
        self._run('action_job_done', jobs)
        self.assertEqual(jobs.x_state, 'done')
        self.assertTrue(jobs.x_closed_at)
        self.assertEqual(plan.x_next_date, today + timedelta(days=30))
        self.assertEqual(self.env['x_hm_meter'].search_count([('x_job_id', '=', jobs.id)]), 1)

    def test_07_original_report_and_view_registration(self):
        report = self.env.ref('hydromotor_service.report_service_protocol')
        self.assertEqual(report.model, 'x_hm_job')
        self.assertEqual(report.report_name, 'hydromotor_service.service_protocol')
        for identifier in ['machine_form', 'job_form', 'plan_form', 'meter_form',
                           'partner_service', 'sale_service', 'product_service']:
            self.assertTrue(self.env.ref('hydromotor_service.' + identifier).active)
        self.assertTrue(self.env.ref('hydromotor_service.service_protocol'))
