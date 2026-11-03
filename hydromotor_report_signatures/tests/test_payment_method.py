"""Disposable PostgreSQL/ORM regressions; never run against production."""
import io
import os
from pathlib import Path
from lxml import etree
from odoo import Command, tools
from odoo.tools.pdf import PdfReader
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install', 'hm_payment_method')
class TestPaymentMethod(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('bg_BG')
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.env.company.country_id = cls.env.ref('base.bg')
        cls.env.company.account_fiscal_country_id = cls.env.ref('base.bg')
        cls.partner_a.country_id = cls.env.ref('base.bg')
        cls.product_a.write({'type': 'service', 'invoice_policy': 'order', 'taxes_id': [Command.clear()]})
        cls.cash = cls.company_data['default_journal_cash'].inbound_payment_method_line_ids[:1]
        cls.bank = cls.company_data['default_journal_bank'].inbound_payment_method_line_ids[:1]
        cls.cash.name = 'HM Cash <safe>'
        cls.bank.name = 'HM Bank'
        cls.company_bank = cls.env['res.partner.bank'].create({
            'partner_id': cls.env.company.partner_id.id, 'acc_number': 'BG80BNBG96611020345678'})

    def _order(self, method=False, bank=None):
        # Construct an invoiceable local fixture, no confirmation/stock/mail actions.
        return self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id, 'state': 'sale',
            'preferred_payment_method_line_id': method.id if method else False,
            'hm_partner_bank_id': (bank or self.company_bank).id,
            'order_line': [Command.create({'product_id': self.product_a.id,
                'product_uom_qty': 1, 'price_unit': 100})]})

    def test_cash_bank_unset_transfer_to_draft_and_explicit_override_survives(self):
        for method in (self.cash, self.bank, False):
            with self.subTest(method=method):
                # An explicit unset on the quotation wins over the customer's default.
                self.partner_a.property_inbound_payment_method_line_id = self.bank
                order = self._order(method)
                invoice = order._create_invoices()
                self.assertEqual(invoice.invoice_payment_term_id, order.payment_term_id)
                self.assertEqual(invoice.preferred_payment_method_line_id, method or self.env['account.payment.method.line'])
                self.assertEqual(invoice.partner_bank_id, self.company_bank)
                self.assertEqual(invoice.state, 'draft')
                self.assertEqual(invoice.payment_state, 'not_paid')
                self.assertFalse(invoice.payment_ids)
                invoice.preferred_payment_method_line_id = self.bank
                order.preferred_payment_method_line_id = self.cash
                self.env.flush_all()
                self.env.invalidate_all()
                self.assertEqual(invoice.preferred_payment_method_line_id, self.bank)

    def test_grouping_keeps_different_methods_and_selected_banks_separate(self):
        other_bank = self.env['res.partner.bank'].create({
            'partner_id': self.env.company.partner_id.id, 'acc_number': 'BG18RZBB91551012345678'})
        for first_method, second_method, second_bank in [
            (self.cash, self.bank, self.company_bank),
            (self.bank, self.bank, other_bank),
            (False, self.bank, self.company_bank),
        ]:
            with self.subTest(first=first_method, second=second_method, bank=second_bank):
                first = self._order(first_method)
                second = self._order(second_method, second_bank)
                invoices = (first | second)._create_invoices(grouped=False)
                self.assertEqual(len(invoices), 2, 'Conflicting document choices must not be silently merged')
                for order in (first, second):
                    invoice = invoices.filtered(lambda move: order in move.invoice_line_ids.sale_line_ids.order_id)
                    self.assertEqual(invoice.preferred_payment_method_line_id, order.preferred_payment_method_line_id)
                    self.assertEqual(invoice.partner_bank_id, order.hm_partner_bank_id)
        compatible = self._order(self.cash) | self._order(self.cash)
        self.assertEqual(len(compatible._create_invoices(grouped=False)), 1)

    def test_invoice_html_preview_prints_actual_method_and_hides_unset(self):
        invoice = self._order(self.cash)._create_invoices()
        html, _ = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)
        dom = etree.HTML(html)
        nodes = dom.xpath("//*[@name='hm_payment_method']")
        self.assertEqual(len(nodes), 2, 'Original and copy must both show the actual payment method')
        self.assertIn('Начин на плащане:', ''.join(nodes[0].itertext()))
        self.assertIn('HM Cash <safe>', ''.join(nodes[0].itertext()))
        self.assertFalse(nodes[0].xpath('.//safe'))
        invoice.preferred_payment_method_line_id = False
        html, _ = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)
        self.assertFalse(etree.HTML(html).xpath("//*[@name='hm_payment_method']"))

    def test_cleared_bank_is_not_merged_with_selected_bank(self):
        selected = self._order(self.bank)
        cleared = self._order(self.bank)
        cleared.hm_partner_bank_id = False
        invoices = (selected | cleared)._create_invoices(grouped=False)
        self.assertEqual(len(invoices), 2)
        empty_invoice = invoices.filtered(lambda move: cleared in move.invoice_line_ids.sale_line_ids.order_id)
        self.assertFalse(empty_invoice.partner_bank_id)

    def test_portal_preview_iframe_and_download_use_invoice_method_bg_en(self):
        for country, label in [('base.bg', 'Начин на плащане:'), ('base.uk', 'Payment Method:')]:
            with self.subTest(country=country):
                self.partner_a.country_id = self.env.ref(country)
                invoice = self._order(self.bank)._create_invoices()
                token = invoice._portal_ensure_token()
                url = '/my/invoices/%s?access_token=%s' % (invoice.id, token)
                response = self.url_open(url)
                self.assertEqual(response.status_code, 200)
                dom = etree.HTML(response.content)
                iframe = dom.xpath("//iframe[@id='invoice_html']/@src")
                self.assertEqual(len(iframe), 1)
                preview = self.url_open(iframe[0])
                self.assertEqual(preview.status_code, 200)
                nodes = etree.HTML(preview.content).xpath("//*[@name='hm_payment_method']")
                self.assertEqual(len(nodes), 2)
                self.assertIn(label, ''.join(nodes[0].itertext()))
                self.assertIn(self.bank.name, ''.join(nodes[0].itertext()))
                self.assertEqual(invoice.payment_state, 'not_paid')
                self.assertFalse(invoice.payment_ids)
                # Do not access/generate an official posted-invoice attachment.
                links = dom.xpath("//a[contains(@class,'o_download_btn')]/@href")
                self.assertEqual(len(links), 1)
                self.assertIn('report_type=pdf', links[0])
                denied = self.url_open('/my/invoices/%s?access_token=invalid&report_type=html' % invoice.id)
                self.assertNotIn(b'HM Bank', denied.content)

    def test_real_invoice_pdf_cash_bank_unset_bg_en(self):
        if os.environ.get('HM_TEST_PDF') != '1':
            self.skipTest('Set HM_TEST_PDF=1 with patched-Qt wkhtmltopdf')
        self.env['ir.config_parameter'].sudo().set_param('report.url',
            os.environ.get('HM_TEST_REPORT_URL') or 'http://127.0.0.1:%s' % tools.config['http_port'])
        renderer = self.env['ir.actions.report'].with_context(force_report_rendering=True)
        out = Path(os.environ['HM_PAYMENT_ARTIFACTS']) if os.environ.get('HM_PAYMENT_ARTIFACTS') else None
        if out:
            out.mkdir(parents=True, exist_ok=True)
        for country, lang, label in [('base.bg', 'bg', 'Начин на плащане:'), ('base.uk', 'en', 'Payment Method:')]:
            self.partner_a.country_id = self.env.ref(country)
            for key, method in [('cash', self.cash), ('bank', self.bank), ('unset', False)]:
                with self.subTest(lang=lang, method=key):
                    invoice = self._order(method)._create_invoices()
                    pdf, kind = renderer._render_qweb_pdf('account.account_invoices', invoice.ids)
                    self.assertEqual(kind, 'pdf')
                    self.assertTrue(pdf.startswith(b'%PDF-'))
                    reader = PdfReader(io.BytesIO(pdf))
                    text = '\n'.join(page.extract_text() for page in reader.pages)
                    # wkhtmltopdf can split Cyrillic words/punctuation into separate PDF text runs.
                    compact = ''.join(text.split())
                    if method:
                        self.assertEqual(compact.count(''.join(label.split())), 2)
                        self.assertEqual(compact.count(''.join(method.name.split())), 2)
                    else:
                        self.assertNotIn(''.join(label.split()), compact)
                    self.assertNotIn('Paid', text)
                    self.assertNotIn('Платена', text)
                    self.assertEqual(invoice.state, 'draft')
                    self.assertEqual(invoice.payment_state, 'not_paid')
                    if out:
                        (out / ('invoice-%s-%s.pdf' % (lang, key))).write_bytes(pdf)
                        (out / ('invoice-%s-%s.txt' % (lang, key))).write_text(text, encoding='utf-8')
