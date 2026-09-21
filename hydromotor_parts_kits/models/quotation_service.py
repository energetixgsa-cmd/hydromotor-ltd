"""Actions for the existing XML-defined models; no replacement of imported data."""
import math
import re

from odoo import api, models
from odoo.exceptions import AccessError, UserError


class PartsQuotationService(models.AbstractModel):
    _name = 'hydromotor.parts.quotation.service'
    _description = 'Навигация и оферти от комплекти части'

    @api.model
    def _require_user(self, sales=False):
        if not self.env.user.has_group('hydromotor_service.group_service_user'):
            raise AccessError('Нужни са права за Машини и сервиз.')
        if sales and not self.env.user.has_group('sales_team.group_sale_salesman'):
            raise AccessError('Нужни са права за продажби.')

    @api.model
    def _record(self, model, record_id):
        record = self.env[model].browse(int(record_id or 0)).exists()
        if not record:
            raise UserError('Записът вече не съществува. Обновете екрана.')
        record.ensure_one()
        record.check_access('read')
        return record

    @api.model
    def _form(self, record):
        return {'type': 'ir.actions.act_window', 'res_model': record._name,
                'res_id': record.id, 'views': [(False, 'form')], 'target': 'current',
                'context': dict(self.env.context)}

    @api.model
    def _catalog_code(self, kit):
        # Only the explicit assembly marker from our catalog imports is parsed.
        # Machine assignment is NEVER inferred from a name or serial number.
        match = re.search(r'Възел\s+(\d+)\s*,\s*чертеж', kit.x_note or '')
        return match.group(1) if match else ''

    @api.model
    def _linked_machines(self, kit):
        return self.env['x_hm_machine'].search([
            ('x_parts_kit_ids', 'in', kit.ids),
            ('x_company_id', '=', kit.x_company_id.id),
        ])

    @api.model
    def _assembly_product(self, kit):
        if kit.x_assembly_product_id:
            return kit.x_assembly_product_id
        code = self._catalog_code(kit)
        products = self.env['product.product']
        if code:
            products = products.search([
                ('default_code', '=', code), ('sale_ok', '=', True),
                '|', ('company_id', '=', False),
                ('company_id', '=', kit.x_company_id.id),
            ], limit=2)
        # Multiple variants with the same code require an explicit choice.
        return products if len(products) == 1 else self.env['product.product']

    @api.model
    def action_open_kit(self, kit_id):
        self._require_user()
        return self._form(self._record('x_hm_parts_kit', kit_id))

    @api.model
    def action_open_machine(self, machine_id):
        self._require_user()
        return self._form(self._record('x_hm_machine', machine_id))

    @api.model
    def action_machine_kits(self, machine_id):
        self._require_user()
        machine = self._record('x_hm_machine', machine_id)
        return {'type': 'ir.actions.act_window', 'name': 'Комплекти — %s' % machine.x_name,
                'res_model': 'x_hm_parts_kit', 'view_mode': 'list,form',
                'domain': [('id', 'in', machine.x_parts_kit_ids.ids)],
                'context': dict(self.env.context, hm_machine_id=machine.id,
                                create=False), 'target': 'current'}

    @api.model
    def action_machine_quotes(self, machine_id):
        self._require_user(sales=True)
        machine = self._record('x_hm_machine', machine_id)
        return {'type': 'ir.actions.act_window', 'name': 'Оферти за части — %s' % machine.x_name,
                'res_model': 'sale.order', 'view_mode': 'list,form',
                'domain': [('order_line.x_hm_parts_machine_id', '=', machine.id)],
                'context': dict(self.env.context), 'target': 'current'}

    @api.model
    def action_start_job(self, job_id):
        self._require_user(sales=True)
        job = self._record('x_hm_job', job_id)
        if not job.x_parts_kit_id:
            raise UserError('Изберете комплект части.')
        return self._start(job.x_parts_kit_id, 'parts', job=job,
                           machine=job.x_machine_id)

    @api.model
    def action_start_line(self, line_id):
        self._require_user(sales=True)
        line = self._record('x_hm_parts_kit_line', line_id)
        return self._start(line.x_kit_id, 'parts', source_line=line)

    @api.model
    def action_start_kit(self, kit_id, mode='parts'):
        self._require_user(sales=True)
        return self._start(self._record('x_hm_parts_kit', kit_id), mode)

    @api.model
    def _start(self, kit, mode, job=None, machine=None, source_line=None):
        if mode not in ('parts', 'assembly'):
            raise UserError('Невалиден начин на офериране.')
        if not kit.x_active:
            raise UserError('Комплектът не е активен.')
        if job and job.x_state == 'cancel':
            raise UserError('Заявката е отказана.')
        machines = self._linked_machines(kit)
        if not machines:
            raise UserError('Комплектът няма свързана машина. Добавете го в досието на машината.')
        if not machine and self.env.context.get('hm_machine_id'):
            machine = self._record('x_hm_machine', self.env.context['hm_machine_id'])
        if machine and machine not in machines:
            raise UserError('Комплектът не е свързан с тази машина.')
        if not machine and len(machines) == 1:
            machine = machines
        order = job.x_sale_order_id if job else self.env['sale.order']
        if job and not order and job.x_repair_id:
            order = job.x_repair_id.sale_order_id
        if order and order.state != 'draft':
            raise UserError('Свързаната оферта трябва да е в чернова, за да добавите позиции.')
        lines = []
        if mode == 'parts':
            for line in kit.x_line_ids:
                lines.append((0, 0, {
                    'x_source_line_id': line.id, 'x_qty': line.x_qty,
                    'x_selected': bool(source_line and line.id == source_line.id),
                }))
        wizard = self.env['x_hm_parts_quote_wizard'].create({
            'x_name': 'Оферта от комплект части', 'x_kit_id': kit.id,
            'x_mode': mode, 'x_machine_id': machine.id if machine else False,
            'x_job_id': job.id if job else False,
            'x_sale_order_id': order.id if order else False,
            'x_assembly_product_id': self._assembly_product(kit).id if mode == 'assembly' else False,
            'x_assembly_qty': 1.0, 'x_line_ids': lines,
        })
        return self._wizard_form(wizard)

    @api.model
    def _wizard_form(self, wizard):
        return {'type': 'ir.actions.act_window', 'name': 'Подготовка на оферта',
                'res_model': wizard._name, 'res_id': wizard.id,
                'views': [(self.env.ref('hydromotor_parts_kits.parts_quote_wizard_form').id, 'form')],
                'target': 'new', 'context': dict(self.env.context)}

    @api.model
    def action_select_lines(self, wizard_id, selected):
        self._require_user(sales=True)
        wizard = self._record('x_hm_parts_quote_wizard', wizard_id)
        if wizard.x_result_order_id:
            return self._form(wizard.x_result_order_id)
        wizard.x_line_ids.write({'x_selected': bool(selected)})
        return self._wizard_form(wizard)

    @api.model
    def _check_product(self, product, company, qty):
        if not product or not product.active or not product.sale_ok:
            raise UserError('Избраният артикул липсва, е архивиран или не е разрешен за продажба.')
        product.check_access('read')
        if product.company_id and product.company_id != company:
            raise UserError('Артикулът принадлежи на друга фирма.')
        if not math.isfinite(qty) or qty <= 0:
            raise UserError('Количеството на всяка избрана позиция трябва да е положително.')

    @api.model
    def _selected_items(self, wizard, kit, company):
        if wizard.x_mode == 'assembly':
            product = wizard.x_assembly_product_id
            code = self._catalog_code(kit)
            if code and product.default_code != code:
                raise UserError('Артикулът на възела трябва да е с каталожен номер %s.' % code)
            self._check_product(product, company, wizard.x_assembly_qty)
            return [(product, wizard.x_assembly_qty, False)]
        if wizard.x_mode != 'parts':
            raise UserError('Невалиден начин на офериране.')
        items = []
        seen = set()
        for line in wizard.x_line_ids.filtered('x_selected'):
            source = line.x_source_line_id
            source.check_access('read')
            if not source or source.x_kit_id != kit or source.id in seen:
                raise UserError('Избраната позиция е дублирана или не принадлежи към комплекта.')
            seen.add(source.id)
            self._check_product(source.x_product_id, company, line.x_qty)
            items.append((source.x_product_id, line.x_qty, source.id))
        if not items:
            raise UserError('Маркирайте поне един артикул за офертата.')
        return items

    @api.model
    def action_apply(self, wizard_id):
        self._require_user(sales=True)
        wizard = self._record('x_hm_parts_quote_wizard', wizard_id)
        wizard.check_access('write')
        # Serialize double-clicks on this user's transient record.
        self.env.cr.execute('SELECT id FROM x_hm_parts_quote_wizard WHERE id = %s FOR UPDATE', [wizard.id])
        wizard.invalidate_recordset()
        if wizard.x_result_order_id:
            wizard.x_result_order_id.check_access('read')
            return self._form(wizard.x_result_order_id)
        kit = wizard.x_kit_id
        machine = wizard.x_machine_id
        job = wizard.x_job_id
        if not machine:
            raise UserError('Изберете конкретна машина.')
        kit.check_access('read')
        machine.check_access('read')
        company = kit.x_company_id
        if not kit.x_active or machine.x_company_id != company or kit not in machine.x_parts_kit_ids:
            raise UserError('Комплектът не е активен или не е свързан с избраната машина и фирма.')
        if company not in self.env.companies:
            raise AccessError('Фирмата не е сред разрешените за текущата сесия.')
        partner = machine.x_partner_id
        if job:
            job.check_access('read')
            if job.x_machine_id != machine or job.x_company_id != company or job.x_state == 'cancel':
                raise UserError('Сервизната заявка не съответства на машината или е отказана.')
            partner = job.x_partner_id
        if not partner:
            raise UserError('В досието или заявката няма клиент за офертата.')
        partner.check_access('read')
        items = self._selected_items(wizard, kit, company)
        order = wizard.x_sale_order_id
        linked = self.env['sale.order']
        if job:
            linked = job.x_sale_order_id or job.x_repair_id.sale_order_id
            if linked and order and linked != order:
                raise UserError('Заявката вече има друга свързана оферта.')
            order = linked or order
        if order:
            order.check_access('write')
            self.env.cr.execute('SELECT id FROM sale_order WHERE id = %s FOR UPDATE', [order.id])
            order.invalidate_recordset()
            if order.state != 'draft' or order.company_id != company or order.partner_id != partner:
                raise UserError('Офертата трябва да е в чернова, за същия клиент и фирма.')
        else:
            if job and job.x_repair_id:
                job.x_repair_id.check_access('write')
                job.x_repair_id.action_create_sale_order()
                order = job.x_repair_id.sale_order_id
                if not order or order.state != 'draft' or order.company_id != company or order.partner_id != partner:
                    raise UserError('Офертата от ремонта не съответства на клиента и фирмата.')
            else:
                order = self.env['sale.order'].with_company(company).create({
                    'partner_id': partner.id, 'company_id': company.id,
                    'origin': '%s / %s' % (machine.x_name, kit.x_name),
                })
        if job and not job.x_sale_order_id:
            job.write({'x_sale_order_id': order.id})
        if not wizard.x_allow_repeat:
            for product, qty, source_id in items:
                duplicate = order.order_line.filtered(lambda line:
                    line.x_hm_parts_kit_id == kit and line.product_id == product
                    and (line.x_hm_parts_machine_id == machine
                         or (job and line.x_hm_job_id == job))
                    and (not line.x_hm_kit_source_line_id
                         or line.x_hm_kit_source_line_id.id == source_id))
                if duplicate:
                    raise UserError('Позиция %s вече присъства в тази оферта. '
                                    'Коригирайте количеството в нея или разрешете повторното добавяне.'
                                    % product.display_name)
        sequence = max(order.order_line.mapped('sequence') or [0]) + 10
        common = {'order_id': order.id, 'x_hm_parts_kit_id': kit.id,
                  'x_hm_parts_machine_id': machine.id,
                  'x_hm_job_id': job.id if job else False}
        line_values = []
        for product, qty, source_id in items:
            line_values.append(dict(common, product_id=product.id, product_uom_qty=qty,
                                    x_hm_kit_source_line_id=source_id, sequence=sequence))
            sequence += 10
        # Odoo computes description, unit, customer pricelist, discount and taxes.
        # No catalog placeholder price is copied over the customer's price.
        self.env['sale.order.line'].with_company(company).create(line_values)
        wizard.write({'x_result_order_id': order.id})
        return self._form(order)
