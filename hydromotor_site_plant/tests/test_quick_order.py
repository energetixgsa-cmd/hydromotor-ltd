import base64
import io
import zipfile
from lxml import etree
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install')
class TestQuickOrder(TransactionCase):
    def test_purchase_export_supplier_code(self):
        partner = self.env['res.partner'].create({'name': 'Local vendor'})
        product = self.env['product.product'].create({'name': 'Local purchase part', 'default_code': 'INTERNAL'})
        self.env['product.supplierinfo'].create({'partner_id': partner.id, 'product_tmpl_id': product.product_tmpl_id.id, 'product_code': '000VENDOR'})
        order = self.env['purchase.order'].create({'partner_id': partner.id, 'order_line': [(0, 0, {'product_id': product.id, 'product_qty': 3})]})
        self.assertTrue(hasattr(order, 'action_hm_quick_order_export'), 'Purchase export missing')
        action = order.action_hm_quick_order_export()
        download = self.env['hm.quick.order.download'].browse(action['res_id'])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(download.file_data))) as archive:
            self.assertIn(b'000VENDOR', archive.read('xl/sharedStrings.xml'))
            self.assertNotIn(b'INTERNAL', archive.read('xl/sharedStrings.xml'))
        arch = self.env['sale.order'].get_view(view_id=self.env.ref('sale.view_order_form').id)['arch']
        self.assertIn('Печат на поръчка', arch)

    def test_bg_total_labels(self):
        self.env['res.lang']._activate_lang('bg_BG')
        currency = self.env.company.currency_id
        totals = {'same_tax_base': True, 'subtotals': [{'name': 'Необложена сума', 'base_amount_currency': 100, 'tax_groups': [{'group_name': 'ДДС 20%', 'display_base_amount_currency': False, 'tax_amount_currency': 20}]}], 'total_amount_currency': 120}
        html = str(self.env['ir.qweb'].with_context(lang='bg_BG')._render('sale.document_tax_totals', {'tax_totals': totals, 'currency': currency, 'oe_subtotal_footer_separator': ''}))
        self.assertIn('Данъчна основа', html)
        self.assertIn('Обща сума по документа', html)
        self.assertNotIn('Необложена сума', html)
        english = str(self.env['ir.qweb'].with_context(lang='en_US')._render('sale.document_tax_totals', {'tax_totals': totals, 'currency': currency, 'oe_subtotal_footer_separator': ''}))
        self.assertIn('Total', english)
        self.assertNotIn('Обща сума по документа', english)

    def test_document_language_overrides_session(self):
        self.env['res.lang']._activate_lang('bg_BG')
        partner = self.env['res.partner'].create({'name': 'Language regression', 'lang': 'en_US'})
        order = self.env['sale.order'].create({'partner_id': partner.id})
        for session_lang, document_lang, expected, forbidden in [
            ('bg_BG', 'en_US', 'Total', 'Данъчна основа'),
            ('en_US', 'bg_BG', 'Данъчна основа', 'Untaxed Amount'),
        ]:
            totals = {'same_tax_base': True, 'subtotals': [{'name': 'Untaxed Amount', 'base_amount_currency': 100, 'tax_groups': [{'group_name': 'VAT', 'display_base_amount_currency': False, 'tax_amount_currency': 0}]}], 'total_amount_currency': 100}
            html = str(self.env['ir.qweb'].with_context(lang=session_lang)._render('sale.document_tax_totals', {'doc': order.with_context(lang=document_lang), 'tax_totals': totals, 'currency': self.env.company.currency_id, 'oe_subtotal_footer_separator': ''}))
            self.assertIn(expected, html)
            self.assertNotIn(forbidden, html)
            self.assertIn('100', html)

    def test_export_preserves_codes(self):
        partner = self.env['res.partner'].create({'name': 'Local export fixture'})
        product = self.env['product.product'].create({'name': 'Local part', 'default_code': '000123-A'})
        order = self.env['sale.order'].create({'partner_id': partner.id, 'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 2})]})
        self.assertTrue(hasattr(order, 'action_hm_quick_order_export'), 'Quick Order export missing')
        before = order.write_date
        action = order.action_hm_quick_order_export()
        wizard = self.env['hm.quick.order.download'].browse(action['res_id'])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(wizard.file_data))) as archive:
            sheet = etree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            ns = {'s': sheet.nsmap[None]}
            cells = sheet.xpath('//s:sheetData/s:row/s:c', namespaces=ns)
            self.assertEqual(len(cells), 2)
            self.assertEqual(cells[0].get('t'), 's')
            self.assertNotEqual(cells[1].get('t'), 's')
            self.assertFalse(sheet.xpath('//s:f', namespaces=ns))
            self.assertIn(b'000123-A', archive.read('xl/sharedStrings.xml'))
        self.assertEqual(order.write_date, before)
        product.default_code = False
        with self.assertRaises(UserError):
            order.action_hm_quick_order_export()
