"""Real Odoo registry/ORM/QWeb checks; run only on a disposable staging test DB.

Not runnable under standalone unittest; source contracts live in tests_source.
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMachineIdentifiers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'HM identifier test customer'})
        cls.product = cls.env['product.product'].create({
            'name': 'HM identifier test machine', 'type': 'consu',
            'is_storable': True, 'tracking': 'serial', 'x_hm_is_machine': True,
        })
        cls.lot = cls.env['stock.lot'].create({
            'name': 'HM-ID-0001', 'product_id': cls.product.id,
            'company_id': cls.env.company.id,
        })
        cls.machine = cls.env['x_hm_machine'].create({
            'x_name': 'HM identifier test dossier', 'x_partner_id': cls.partner.id,
            'x_company_id': cls.env.company.id, 'x_lot_id': cls.lot.id,
        })

    def test_fields_are_optional_stored_indexed_uncopied_chars(self):
        for name in ('x_registration_number', 'x_engine_number'):
            field = self.machine._fields[name]
            self.assertEqual(field.type, 'char')
            self.assertTrue(field.store)
            self.assertTrue(field.index)
            self.assertFalse(field.required)
            self.assertFalse(field.readonly)
            self.assertFalse(field.copy)
            self.assertFalse(self.machine[name])

    def test_text_roundtrip_and_search_preserve_identifiers(self):
        values = {'x_registration_number': 'СВ 0012 АВ', 'x_engine_number': '000045-A/Б'}
        self.machine.write(values)
        self.machine.flush_recordset(list(values))
        self.machine.invalidate_recordset(list(values))
        for name, value in values.items():
            self.assertEqual(self.machine[name], value)
            found = self.env['x_hm_machine'].search([(name, '=', value)])
            self.assertIn(self.machine, found)
        self.machine.write(dict.fromkeys(values, False))
        self.assertFalse(self.machine.x_registration_number)
        self.assertFalse(self.machine.x_engine_number)

    def test_duplicate_does_not_copy_new_identifiers(self):
        self.machine.write({'x_registration_number': 'СВ 0012 АВ', 'x_engine_number': '000045-A'})
        lot = self.env['stock.lot'].create({
            'name': 'HM-ID-0002', 'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        # The dossier's existing unique company/lot identity requires a NEW lot.
        duplicate = self.machine.copy({'x_lot_id': lot.id, 'x_identity_key': False})
        self.assertFalse(duplicate.x_registration_number)
        self.assertFalse(duplicate.x_engine_number)
        self.assertEqual(self.machine.x_engine_number, '000045-A')

    def test_effective_form_including_optional_sales_inheritance(self):
        views = [self.env.ref('hydromotor_service.machine_form')]
        registry = self.env.ref('hydromotor_machine_sales.machine_registry_form',
                                raise_if_not_found=False)
        if registry:
            views.append(registry)
        for view in views:
            arch = view._get_combined_arch()
            for name in ('x_registration_number', 'x_engine_number'):
                nodes = arch.xpath(".//field[@name='%s']" % name)
                self.assertEqual(len(nodes), 1)
                self.assertFalse(nodes[0].get('readonly'))
                self.assertFalse(nodes[0].get('invisible'))

    def test_protocol_only_displays_present_identifiers(self):
        job = self.env['x_hm_job'].create({
            'x_name': 'HM identifier test protocol', 'x_machine_id': self.machine.id,
            'x_company_id': self.env.company.id, 'x_partner_id': self.partner.id,
            'x_technician_id': self.env.uid,
        })
        def render():
            return self.env['ir.actions.report']._render_qweb_html(
                'hydromotor_service.report_service_protocol', job.ids)[0].decode('utf-8')

        for registration, engine in [(False, False), ('СВ 0012 АВ', False),
                                     (False, '000045-A'), ('СВ 0012 АВ', '000045-A')]:
            self.machine.write({'x_registration_number': registration, 'x_engine_number': engine})
            html = render()
            self.assertEqual('Регистрационен номер' in html, bool(registration))
            self.assertEqual('Номер на двигателя' in html, bool(engine))
            if registration:
                self.assertIn(registration, html)
            if engine:
                self.assertIn(engine, html)
