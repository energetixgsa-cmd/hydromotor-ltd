from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestArticleReference(TransactionCase):
    """Run on Odoo.sh development with --test-tags /hydromotor_report_naming."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Hydraulic seal', 'default_code': '000123-A',
            'type': 'consu', 'list_price': 15.0,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Article column test'})

    def test_display_name_and_search(self):
        for model in (self.product, self.product.product_tmpl_id):
            for context in ({}, {'display_default_code': True}, {'display_default_code': False}, {'formatted_display_name': True}):
                self.assertEqual(model.with_context(**context).display_name, 'Hydraulic seal')
        result = self.env['product.product'].search([('display_name', 'ilike', '000123-A')])
        self.assertIn(self.product, result)

    def test_old_description_preserved_and_explicit_edit(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        original = '[000123-A] Hydraulic seal\nCustom dimensions [20 mm]'
        line = self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': self.product.id,
            'product_uom_qty': 2, 'price_unit': 15, 'name': original,
        })
        self.assertEqual(line.hm_article_number, '000123-A')
        self.assertEqual(line.hm_description, 'Hydraulic seal\nCustom dimensions [20 mm]')
        self.assertEqual(line.name, original)
        line.hm_description = 'Hydraulic seal\nRevised dimensions [25 mm]'
        self.assertEqual(line.name, 'Hydraulic seal\nRevised dimensions [25 mm]')
        self.assertEqual(line.price_unit, 15)
        self.assertEqual(line.product_uom_qty, 2)

    def test_notes_and_missing_code(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        note = self.env['sale.order.line'].create({
            'order_id': order.id, 'display_type': 'line_note',
            'name': '[000123-A] Keep this note verbatim',
        })
        self.assertEqual(note.hm_description, note.name)
        self.assertFalse(note.hm_article_number)
        self.product.default_code = False
        self.assertEqual(self.product.display_name, 'Hydraulic seal')

    def test_sale_html_report(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': self.product.id,
            'product_uom_qty': 1, 'price_unit': 15,
            'name': '[000123-A] Hydraulic seal\nKeep these dimensions',
        })
        html, _ = self.env['ir.actions.report']._render_qweb_html(
            'sale.action_report_saleorder', order.ids,
        )
        text = html.decode()
        self.assertIn('hm_th_article_number', text)
        self.assertIn('000123-A', text)
        self.assertIn('Keep these dimensions', text)
        self.assertNotIn('[000123-A] Hydraulic seal', text)
