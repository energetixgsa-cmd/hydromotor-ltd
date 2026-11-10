import base64
import io
import zipfile
from lxml import etree
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install')
class TestQuickOrder(TransactionCase):
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
