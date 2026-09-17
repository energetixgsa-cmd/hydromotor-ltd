"""Odoo integration checks supplied for a disposable 19.0 database.

These tests have NOT been run in the preparation environment.
They create only fictional records within Odoo TransactionCase rollbacks.
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestRecoveredConfigurator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'HM 19 TEST - Fictional configurator customer',
        })
        cls.base = cls.env['x_hm_base'].create({
            'x_name': 'Fictional 42-5 .16 H', 'x_code': 'HM_TEST_BASE',
            'x_version': 'HM_TEST_ONLY', 'x_family': '42-5', 'x_price': 1000.0,
        })
        cls.option = cls.env['x_hm_option'].create({
            'x_name': 'Fictional test option', 'x_code': 'HM_TEST_OPTION',
            'x_version': 'HM_TEST_ONLY', 'x_families': '42-5', 'x_price': 100.0,
        })
        cls.cfg = cls.env['x_hm_config'].create({
            'x_name': 'Fictional test configuration',
            'x_company_id': cls.env.company.id, 'x_partner_id': cls.partner.id,
            'x_base_id': cls.base.id, 'x_quantity': 2, 'x_discount': 10.0,
            'x_chassis_price': 50.0, 'x_transport_price': 25.0,
            'x_market': 'EU', 'x_chassis_type': 'unspecified', 'x_language': 'bg',
        })

    def _check_config(self):
        self.env.ref('hydromotor_machine_sales.check_config').with_context(
            active_model='x_hm_config', active_id=self.cfg.id,
            active_ids=self.cfg.ids,
        ).run()

    def test_01_separate_option_guards(self):
        write = self.env.ref('hydromotor_machine_sales.options_guard')
        unlink = self.env.ref('hydromotor_machine_sales.options_unlink')
        self.assertTrue(write.action_server_ids)
        self.assertTrue(unlink.action_server_ids)
        self.assertFalse(write.action_server_ids & unlink.action_server_ids)
        self.assertEqual(write.action_server_ids.code, unlink.action_server_ids.code)

    def test_02_base_configuration_totals(self):
        self._check_config()
        self.assertAlmostEqual(self.cfg.x_unit_price, 975.0, places=2)
        self.assertAlmostEqual(self.cfg.x_total, 1950.0, places=2)
        self.assertTrue(self.cfg.x_result)

    def test_03_option_change_and_recalculation(self):
        revision = self.cfg.x_build_revision
        line = self.env['x_hm_config_line'].create({
            'x_config_id': self.cfg.id, 'x_option_id': self.option.id,
        })
        self.assertGreater(self.cfg.x_build_revision, revision)
        self._check_config()
        self.assertAlmostEqual(self.cfg.x_total, 2130.0, places=2)
        line.unlink()
        self._check_config()
        self.assertAlmostEqual(self.cfg.x_total, 1950.0, places=2)

    def test_04_public_user_cannot_read_custom_business_models(self):
        public = self.env.ref('base.public_user')
        acl = self.env['ir.model.access'].with_user(public)
        for model in ['x_hm_config', 'x_hm_config_line', 'x_hm_release', 'x_hm_bridge']:
            self.assertFalse(acl.check(model, 'read', raise_exception=False))
