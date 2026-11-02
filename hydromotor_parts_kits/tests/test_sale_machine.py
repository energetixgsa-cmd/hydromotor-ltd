"""Real registry/SQL tests. No sales confirmation, stock validation or mail send."""
from odoo import Command, tools
import io
import os
from pathlib import Path
from odoo.tools.pdf import PdfReader
from odoo.tests import Form, TransactionCase, tagged
from lxml import etree
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user
from odoo.tools.safe_eval import safe_eval


@tagged('post_install', '-at_install', 'hm_sale_machine')
class TestSaleMachine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'HM machine selection test'})
        cls.other_partner = cls.env['res.partner'].create({'name': 'HM other customer'})
        cls.product = cls.env['product.product'].create({'name': 'HM test spare', 'type': 'consu'})
        cls.machine_product = cls.env['product.product'].create({
            'name': 'HM serial machine', 'type': 'consu', 'is_storable': True, 'tracking': 'serial'})
        cls.machine = cls._machine('HM-00001')
        cls.second_machine = cls._machine('HM-00002')

    @classmethod
    def _machine(cls, serial, partner=None, company=None):
        company = company or cls.env.company
        lot = cls.env['stock.lot'].with_company(company).create({
            'name': serial, 'product_id': cls.machine_product.id, 'company_id': company.id})
        return cls.env['x_hm_machine'].with_company(company).create({
            'x_name': 'HM Model ' + serial, 'x_model_label': 'HM Model', 'x_lot_id': lot.id,
            'x_partner_id': (partner or cls.partner).id, 'x_company_id': company.id})

    def _order(self, **values):
        return self.env['sale.order'].create({'partner_id': self.partner.id,
            'x_hm_order_machine_id': self.machine.id, **values})

    def _line(self, order, **values):
        return self.env['sale.order.line'].create({'order_id': order.id,
            'product_id': self.product.id, 'product_uom_qty': 2, **values})

    def test_order_machine_default_reaches_lines_and_is_read_back(self):
        self.assertIn('x_hm_order_machine_id', self.env['sale.order']._fields,
                      'Order machine selector is missing')
        order = self._order(order_line=[Command.create({'product_id': self.product.id})])
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(order.x_hm_order_machine_id, self.machine)
        self.assertEqual(order.order_line.x_hm_parts_machine_id, self.machine)
        self.assertTrue(order.order_line.x_hm_use_order_machine)
        self.assertTrue(order._fields['x_hm_order_machine_id'].store)
        self.assertFalse(order.copy().x_hm_order_machine_id)
        self.assertFalse(order.copy().order_line.x_hm_parts_machine_id)

    def test_header_change_updates_only_inherited_lines_and_preserves_explicit_false(self):
        order = self._order()
        inherited = self._line(order)
        explicit = self._line(order, x_hm_parts_machine_id=self.second_machine.id)
        unassigned = self._line(order, x_hm_parts_machine_id=False)
        note = self.env['sale.order.line'].create({'order_id': order.id,
            'display_type': 'line_note', 'name': 'No attribution on notes'})
        self.assertFalse(note.x_hm_parts_machine_id)
        self.assertFalse(explicit.x_hm_use_order_machine)
        order.x_hm_order_machine_id = self.second_machine
        self.assertEqual(inherited.x_hm_parts_machine_id, self.second_machine)
        self.assertEqual(explicit.x_hm_parts_machine_id, self.second_machine)
        self.assertFalse(unassigned.x_hm_parts_machine_id)
        order.x_hm_order_machine_id = False
        self.assertFalse(inherited.x_hm_parts_machine_id)
        self.assertEqual(explicit.x_hm_parts_machine_id, self.second_machine)
        inherited.write({'x_hm_parts_machine_id': self.machine.id})
        self.assertFalse(inherited.x_hm_use_order_machine)
        inherited.write({'x_hm_use_order_machine': True})
        self.assertFalse(inherited.x_hm_parts_machine_id)

    def test_exact_web_save_header_onchange_echo_preserves_inheritance(self):
        # Captured staging request: [[49], {"x_hm_order_machine_id":45,
        # "order_line":[[1,65,{"x_hm_parts_machine_id":45}]]}].
        # Only database IDs are rebound to isolated transaction fixtures.
        order = self._order()
        inherited = self._line(order)
        override = self._line(order, x_hm_parts_machine_id=self.second_machine.id)
        cleared = self._line(order, x_hm_parts_machine_id=False)
        args = [[order.id], {'x_hm_order_machine_id': self.second_machine.id,
            'order_line': [[1, inherited.id, {'x_hm_parts_machine_id': self.second_machine.id}]]}]
        self.env['sale.order'].browse(args[0]).web_save(args[1], specification={})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertTrue(inherited.x_hm_use_order_machine,
                        'Unchanged true flag omitted by web_save must survive the onchange echo')
        self.assertEqual(inherited.x_hm_parts_machine_id, self.second_machine)
        order.web_save({'x_hm_order_machine_id': self.machine.id,
            'order_line': [[1, inherited.id, {'x_hm_parts_machine_id': self.machine.id}]]}, specification={})
        self.assertTrue(inherited.x_hm_use_order_machine)
        self.assertEqual(inherited.x_hm_parts_machine_id, self.machine)
        self.assertFalse(override.x_hm_use_order_machine)
        self.assertEqual(override.x_hm_parts_machine_id, self.second_machine)
        self.assertFalse(cleared.x_hm_use_order_machine)
        self.assertFalse(cleared.x_hm_parts_machine_id)

    def test_web_save_header_echo_does_not_swallow_override_or_clear(self):
        order = self._order()
        explicit = self._line(order, x_hm_parts_machine_id=self.second_machine.id)
        opt_out = self._line(order)
        different = self._line(order)
        cleared = self._line(order)
        order.web_save({'x_hm_order_machine_id': self.second_machine.id, 'order_line': [
            [1, explicit.id, {'x_hm_parts_machine_id': self.second_machine.id}],
            [1, opt_out.id, {'x_hm_parts_machine_id': self.second_machine.id,
                             'x_hm_use_order_machine': False}],
            [1, different.id, {'x_hm_parts_machine_id': self.machine.id}],
            [1, cleared.id, {'x_hm_parts_machine_id': False}],
        ]}, specification={})
        for line in (explicit, opt_out, different, cleared):
            self.assertFalse(line.x_hm_use_order_machine)
        self.assertEqual(different.x_hm_parts_machine_id, self.machine)
        self.assertFalse(cleared.x_hm_parts_machine_id)
        order.x_hm_order_machine_id = self.machine
        self.assertEqual(explicit.x_hm_parts_machine_id, self.second_machine)
        self.assertEqual(opt_out.x_hm_parts_machine_id, self.second_machine)
        self.assertFalse(cleared.x_hm_parts_machine_id)

    def test_web_save_header_clear_echo_keeps_inheritance_and_direct_clear_opts_out(self):
        order = self._order()
        inherited = self._line(order)
        order.web_save({'x_hm_order_machine_id': False,
            'order_line': [[1, inherited.id, {'x_hm_parts_machine_id': False}]]}, specification={})
        self.assertTrue(inherited.x_hm_use_order_machine)
        self.assertFalse(inherited.x_hm_parts_machine_id)
        order.x_hm_order_machine_id = self.machine
        self.assertEqual(inherited.x_hm_parts_machine_id, self.machine)
        order.web_save({'order_line': [[1, inherited.id, {'x_hm_parts_machine_id': False}]]}, specification={})
        self.assertFalse(inherited.x_hm_use_order_machine)
        order.x_hm_order_machine_id = self.second_machine
        self.assertFalse(inherited.x_hm_parts_machine_id)

    def test_machine_customer_helper_has_distinct_label(self):
        metadata = self.env['sale.order'].fields_get(
            ['x_hm_machine_customer_id', 'commercial_partner_id'], attributes=['string'])
        self.assertNotEqual(metadata['x_hm_machine_customer_id']['string'],
                            metadata.get('commercial_partner_id', {}).get('string', 'Commercial Entity'))
        self.assertNotEqual(metadata['x_hm_machine_customer_id']['string'], 'Commercial Entity')

    def test_rpc_rejects_wrong_customer_retired_and_wrong_company(self):
        order = self._order()
        wrong = self._machine('HM-WRONG-OWNER', partner=self.other_partner)
        retired = self._machine('HM-RETIRED')
        retired.x_retired = True
        other_company = self.env['res.company'].create({'name': 'HM isolated company'})
        foreign = self._machine('HM-OTHER-COMPANY', company=other_company)
        for machine in (wrong, retired, foreign):
            with self.subTest(machine=machine.id):
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    self._order(x_hm_order_machine_id=machine.id)
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    self._line(order, x_hm_parts_machine_id=machine.id)
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    order.write({'x_hm_order_machine_id': machine.id})
        self._line(order, x_hm_parts_machine_id=self.second_machine.id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.write({'partner_id': self.other_partner.id, 'x_hm_order_machine_id': False})
        self.assertEqual(order.partner_id, self.partner)

    def test_same_commercial_customer_contacts_are_accepted(self):
        contact = self.env['res.partner'].create({'name': 'HM site contact', 'parent_id': self.partner.id})
        order = self._order(partner_id=contact.id)
        self.assertEqual(self._line(order).x_hm_parts_machine_id, self.machine)

    def test_form_machine_immediately_under_customer_and_line_defaults_override(self):
        arch = etree.fromstring(self.env['sale.order'].get_view(
            view_id=self.env.ref('sale.view_order_form').id, view_type='form')['arch'])
        selector = arch.xpath("//group[@name='partner_details']/field[@name='partner_id']/following-sibling::*[1]")
        self.assertTrue(selector and selector[0].get('name') == 'x_hm_order_machine_id',
                        'Selector must be directly under customer, not hidden in a tab')
        self.assertTrue(arch.xpath("//field[@name='order_line']/list/field[@name='x_hm_parts_machine_id']"))
        with Form(self.env['sale.order']) as form:
            form.partner_id = self.partner
            form.x_hm_order_machine_id = self.machine
            with form.order_line.new() as line:
                line.product_id = self.product
                self.assertTrue(line.x_hm_use_order_machine)
                self.assertEqual(line.x_hm_parts_machine_id, self.machine)
            with form.order_line.new() as line:
                line.product_id = self.product
                line.x_hm_use_order_machine = False
                line.x_hm_parts_machine_id = self.second_machine
            form.x_hm_order_machine_id = self.second_machine
        self.assertEqual(form.record.order_line[0].x_hm_parts_machine_id, self.second_machine)
        self.assertFalse(form.record.order_line[1].x_hm_use_order_machine)
        self.assertEqual(form.record.x_hm_order_machine_serial, self.second_machine.x_serial)
        self.assertEqual(form.record.x_hm_order_machine_label, 'HM Model')

    def test_dossier_history_is_actual_attributed_lines_not_installation(self):
        self.assertIn('x_hm_parts_sale_line_ids', self.machine._fields,
                      'Dossier sale-line history is missing')
        original_sale = self._order(x_hm_order_machine_id=False)
        self.machine.x_sale_order_id = original_sale
        order = self._order()
        line = self._line(order)
        explicit = self._line(order, x_hm_parts_machine_id=self.second_machine.id)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertIn(line, self.machine.x_hm_parts_sale_line_ids)
        self.assertNotIn(explicit, self.machine.x_hm_parts_sale_line_ids)
        self.assertIn(explicit, self.second_machine.x_hm_parts_sale_line_ids)
        self.assertEqual(line.x_hm_parts_history_state, 'offered')
        self.assertEqual(self.machine.x_sale_order_id, original_sale)
        self.assertIn(self.machine, original_sale.x_hm_machine_ids)
        self.assertFalse(order.x_hm_machine_ids)
        # Synthetic unsaved quantities exercise classification, not stock transitions.
        for state, delivered, expected in [('sale', 0, 'sold'), ('sale', 1, 'part_delivered'),
                                           ('sale', 2, 'delivered'), ('cancel', 2, 'cancelled')]:
            pseudo = self.env['sale.order.line'].new({'state': state,
                'product_uom_qty': 2, 'qty_delivered': delivered})
            pseudo._compute_hm_parts_history_state()
            self.assertEqual(pseudo.x_hm_parts_history_state, expected)
        page = self.env.ref('hydromotor_parts_kits.machine_form_parts_history')
        history_arch = etree.fromstring(page.arch_db)
        self.assertTrue(history_arch.xpath("//field[@name='x_hm_parts_sale_line_ids']/list[@create='false'][@edit='false'][@delete='false']"))

    def test_real_sale_and_invoice_style_proforma_qweb_print_mixed_machines(self):
        combined = self.env.ref('sale.report_saleorder_document')._get_combined_arch()
        self.assertTrue(combined.xpath("//td[@name='td_product_name']//div[contains(@class,'hm-machine-line')]"),
                        'Product cell attribution missing from combined report; multi-match xpath only applies once')
        order = self._order()
        self._line(order, name='Inherited spare')
        self._line(order, name='Override spare', x_hm_parts_machine_id=self.second_machine.id)
        self._line(order, name='Unassigned spare', x_hm_parts_machine_id=False)
        self.second_machine.x_model_label = 'Second <safe> model'
        for report in ('sale.action_report_saleorder', 'sale.action_report_pro_forma_invoice'):
            with self.subTest(report=report):
                html, _ = self.env['ir.actions.report']._render_qweb_html(report, order.ids)
                dom = etree.HTML(html)
                header = dom.xpath("//*[contains(@class,'hm-machine-default')]")
                self.assertEqual(len(header), 1, 'Actual report must include default machine header')
                self.assertIn('HM-00001', ''.join(header[0].itertext()))
                attributed = dom.xpath("//*[contains(@class,'hm-machine-line')]")
                self.assertEqual(len(attributed), 2, 'No order fallback on explicitly unassigned line')
                self.assertIn('HM-00001', ''.join(attributed[0].itertext()))
                self.assertIn('HM-00002', ''.join(attributed[1].itertext()))
                self.assertIn('Second <safe> model', ''.join(attributed[1].itertext()))
                self.assertFalse(attributed[1].xpath('.//safe'))
        order.x_hm_order_machine_id = False
        html, _ = self.env['ir.actions.report']._render_qweb_html('sale.action_report_saleorder', order.ids)
        dom = etree.HTML(html)
        self.assertFalse(dom.xpath("//*[contains(@class,'hm-machine-default')]"))
        self.assertEqual(len(dom.xpath("//*[contains(@class,'hm-machine-line')]")), 1)

    def test_sales_role_can_attribute_but_cannot_modify_machine_or_read_other_company(self):
        user = new_test_user(self.env, login='hm_machine_sales_test',
            context={'no_reset_password': True, 'mail_create_nosubscribe': True},
            groups='sales_team.group_sale_salesman', company_id=self.env.company.id,
            company_ids=[Command.set(self.env.company.ids)])
        self.assertTrue(self.machine.with_user(user).has_access('read'),
                        'Sales role needs read-only machine access for selection')
        order = self.env['sale.order'].with_user(user).create({
            'partner_id': self.partner.id, 'x_hm_order_machine_id': self.machine.id})
        line = self.env['sale.order.line'].with_user(user).create({
            'order_id': order.id, 'product_id': self.product.id})
        self.assertEqual(line.x_hm_parts_machine_id, self.machine.with_user(user))
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.machine.with_user(user).write({'x_notes': 'not allowed'})
        other_company = self.env['res.company'].create({'name': 'HM forbidden company'})
        foreign = self._machine('HM-INACCESSIBLE', company=other_company)
        with self.assertRaises(AccessError), self.cr.savepoint():
            foreign.with_user(user).read(['x_name'])
        self.assertFalse(self.env['x_hm_machine'].with_user(user).search([('id', '=', foreign.id)]))
        # Actual restricted-user report rendering must not rely on sudo callbacks.
        html, _ = self.env['ir.actions.report'].with_user(user)._render_qweb_html(
            'sale.action_report_saleorder', order.ids)
        self.assertIn(b'HM-00001', html)

    def test_context_defaults_batch_create_and_line_reparenting(self):
        order = self._order()
        from_context = self.env['sale.order.line'].with_context(default_order_id=order.id).create({
            'product_id': self.product.id})
        self.assertEqual(from_context.x_hm_parts_machine_id, self.machine,
                         'Order context defaults must work for catalog/configurator lines')
        explicit = self.env['sale.order.line'].with_context(default_order_id=order.id,
            default_x_hm_parts_machine_id=self.second_machine.id).create({'product_id': self.product.id})
        self.assertEqual(explicit.x_hm_parts_machine_id, self.second_machine)
        self.assertFalse(explicit.x_hm_use_order_machine)
        other_order = self._order(x_hm_order_machine_id=self.second_machine.id)
        lines = self.env['sale.order.line'].create([
            {'order_id': order.id, 'product_id': self.product.id},
            {'order_id': other_order.id, 'product_id': self.product.id}])
        self.assertEqual(lines[0].x_hm_parts_machine_id, self.machine)
        self.assertEqual(lines[1].x_hm_parts_machine_id, self.second_machine)
        from_context.order_id = other_order
        self.assertEqual(from_context.x_hm_parts_machine_id, self.second_machine)

    def test_ui_explicit_context_false_is_not_reinterpreted_as_inheritance(self):
        fields = ['x_hm_parts_machine_id', 'x_hm_use_order_machine']
        defaults = self.env['sale.order.line'].with_context(
            default_x_hm_parts_machine_id=False).default_get(fields)
        self.assertFalse(defaults['x_hm_use_order_machine'],
                         'An explicitly empty machine is an opt-out, including context defaults')
        defaults = self.env['sale.order.line'].with_context(
            default_x_hm_use_order_machine=False).default_get(fields)
        self.assertFalse(defaults['x_hm_use_order_machine'])

    def test_selector_domain_uses_commercial_root_and_excludes_wrong_or_retired(self):
        arch = etree.fromstring(self.env['sale.order'].get_view(
            view_id=self.env.ref('sale.view_order_form').id, view_type='form')['arch'])
        selector = arch.xpath("//group[@name='partner_details']/field[@name='x_hm_order_machine_id']")[0]
        # View domains contain names: literal_eval is wrong here. Bind the exact
        # client-side variables and let Odoo evaluate the domain expression.
        domain = safe_eval(selector.get('domain'), {'company_id': self.env.company.id,
            'x_hm_machine_customer_id': self.partner.id})
        wrong = self._machine('HM-DOMAIN-OTHER', partner=self.other_partner)
        retired = self._machine('HM-DOMAIN-RETIRED')
        retired.x_retired = True
        matches = self.env['x_hm_machine'].search(domain)
        self.assertIn(self.machine, matches)
        self.assertIn(self.second_machine, matches)
        self.assertNotIn(wrong, matches)
        self.assertNotIn(retired, matches)
        self.assertEqual(selector.get('readonly'), "state not in ['draft','sent']")
        metadata = self.env['sale.order'].fields_get(['x_hm_order_machine_id'],
            attributes=['store', 'searchable', 'type'])['x_hm_order_machine_id']
        self.assertTrue(metadata['store'] and metadata['searchable'])

    def test_bulgarian_actual_report_labels(self):
        self.env['res.lang']._activate_lang('bg_BG')
        self.partner.country_id = self.env.ref('base.bg')
        order = self._order()
        self._line(order)
        for report in ('sale.action_report_saleorder', 'sale.action_report_pro_forma_invoice'):
            html, _ = self.env['ir.actions.report']._render_qweb_html(report, order.ids)
            text = html.decode('utf-8')
            self.assertIn('Машина:', text)
            self.assertIn('Сериен №:', text)
            self.assertIn('HM-00001', text)

    def test_real_sale_and_proforma_pdf_machine_text(self):
        if os.environ.get('HM_TEST_PDF') != '1':
            self.skipTest('Set HM_TEST_PDF=1 with patched-Qt wkhtmltopdf for PDF acceptance')
        self.env['ir.config_parameter'].set_param(
            'report.url', os.environ.get('HM_TEST_REPORT_URL') or
            'http://127.0.0.1:%s' % tools.config['http_port'])
        self.second_machine.x_model_label = 'Second <safe> model'
        order = self._order()
        self._line(order, name='Inherited spare')
        self._line(order, name='Override spare', x_hm_parts_machine_id=self.second_machine.id)
        self._line(order, name='Unassigned spare', x_hm_parts_machine_id=False)
        renderer = self.env['ir.actions.report'].with_context(force_report_rendering=True)
        for label, report in [('sale', 'sale.action_report_saleorder'),
                              ('proforma', 'sale.action_report_pro_forma_invoice')]:
            pdf, kind = renderer._render_qweb_pdf(report, order.ids)
            self.assertEqual(kind, 'pdf')
            self.assertTrue(pdf.startswith(b'%PDF-'), 'Must be real PDF, not Odoo test-mode HTML fallback')
            reader = PdfReader(io.BytesIO(pdf))
            text = '\n'.join(page.extract_text() for page in reader.pages)
            self.assertEqual(text.count('HM-00001'), 2, 'Header plus inherited line only')
            self.assertEqual(text.count('HM-00002'), 1, 'Override line only')
            self.assertIn('HM Model', text)
            self.assertIn('Second <safe> model', text)
            self.assertIn('Unassigned spare', text)
            destination = os.environ.get('HM_TEST_ARTIFACT_DIR')
            if destination:
                path = Path(destination)
                path.mkdir(parents=True, exist_ok=True)
                (path / ('machine-' + label + '.pdf')).write_bytes(pdf)
