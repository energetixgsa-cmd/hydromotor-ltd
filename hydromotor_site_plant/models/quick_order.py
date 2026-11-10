import base64
import io
import math
import xlsxwriter
from odoo import fields, models, _
from odoo.exceptions import UserError


class QuickOrderDownload(models.TransientModel):
    _name = 'hm.quick.order.download'
    _description = 'Quick Order Excel download'

    file_data = fields.Binary(readonly=True, attachment=False)
    filename = fields.Char(readonly=True)


class PurchaseOrderQuickOrder(models.Model):
    _inherit = 'purchase.order'

    def action_hm_quick_order_export(self):
        self.ensure_one()
        self.check_access('read')
        lines = self.order_line.filtered(lambda line: not line.display_type)
        if not lines:
            raise UserError(_('Няма продуктови редове за експорт.'))
        stream = io.BytesIO()
        with xlsxwriter.Workbook(stream, {'in_memory': True}) as workbook:
            sheet = workbook.add_worksheet('Quick Order')
            text_format = workbook.add_format({'num_format': '@'})
            sheet.set_column(0, 0, 24, text_format)
            sheet.set_column(1, 1, 14)
            for index, line in enumerate(lines):
                seller = line.product_id.with_company(self.company_id)._select_seller(
                    partner_id=self.partner_id, quantity=line.product_qty,
                    date=self.date_order.date(), uom_id=line.product_uom_id)
                code = seller.product_code or line.product_id.default_code
                if not code or not code.strip():
                    raise UserError(_('Липсва номер на частта: %s', line.name))
                if not math.isfinite(line.product_qty) or line.product_qty <= 0:
                    raise UserError(_('Количеството трябва да е положително: %s', code))
                if line.product_uom_id != line.product_id.uom_id:
                    raise UserError(_('Различна мерна единица за %s. Използвайте основната единица на продукта.', code))
                sheet.write_string(index, 0, code, text_format)
                sheet.write_number(index, 1, line.product_qty)
        download = self.env['hm.quick.order.download'].create({
            'filename': 'QuickOrder_%s.xlsx' % self.name.replace('/', '_'),
            'file_data': base64.b64encode(stream.getvalue()),
        })
        return {'type': 'ir.actions.act_window', 'name': _('Експорт за Quick Order'),
                'res_model': download._name, 'res_id': download.id,
                'view_mode': 'form', 'target': 'new'}


class SaleOrderQuickOrder(models.Model):
    _inherit = 'sale.order'

    def action_hm_quick_order_export(self):
        self.ensure_one()
        self.check_access('read')
        lines = self.order_line.filtered(lambda line: not line.display_type)
        if not lines:
            raise UserError(_('Няма продуктови редове за експорт.'))
        rows = []
        for line in lines:
            code = line.product_id.default_code
            quantity = line.product_uom_qty
            if not code or not code.strip():
                raise UserError(_('Липсва номер на частта: %s', line.name))
            if not math.isfinite(quantity) or quantity <= 0:
                raise UserError(_('Количеството трябва да е положително: %s', code))
            if line.product_uom_id != line.product_id.uom_id:
                raise UserError(_('Различна мерна единица за %s. Използвайте основната единица на продукта.', code))
            rows.append((code, quantity))
        stream = io.BytesIO()
        with xlsxwriter.Workbook(stream, {'in_memory': True}) as workbook:
            sheet = workbook.add_worksheet('Quick Order')
            text_format = workbook.add_format({'num_format': '@'})
            sheet.set_column(0, 0, 24, text_format)
            sheet.set_column(1, 1, 14)
            for index, (code, quantity) in enumerate(rows):
                sheet.write_string(index, 0, code, text_format)
                sheet.write_number(index, 1, quantity)
        download = self.env['hm.quick.order.download'].create({
            'filename': 'QuickOrder_%s.xlsx' % self.name.replace('/', '_'),
            'file_data': base64.b64encode(stream.getvalue()),
        })
        return {
            'type': 'ir.actions.act_window', 'name': _('Експорт за Quick Order'),
            'res_model': download._name, 'res_id': download.id,
            'view_mode': 'form', 'target': 'new',
        }
