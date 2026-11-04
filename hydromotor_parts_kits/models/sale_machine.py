"""Sales attribution for existing customer machines, separate from machine sales."""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .sale_machine_policy import machine_link_error, parts_history_state, prepare_line_values


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_hm_order_machine_id = fields.Many2one(
        'x_hm_machine', string='Машина за офертата', copy=False,
        index=True, ondelete='restrict',
        help='Машина на клиента за частите/услугите; не е първоначалната продажба на машината.')

    x_hm_machine_customer_id = fields.Many2one(
        related='partner_id.commercial_partner_id', string='Клиент за избор на машина', compute_sudo=False)
    x_hm_order_machine_label = fields.Char(
        related='x_hm_order_machine_id.x_model_label', string='Модел машина', compute_sudo=False)
    x_hm_order_machine_serial = fields.Char(
        related='x_hm_order_machine_id.x_serial', string='Сериен номер', compute_sudo=False)

    def _hm_report_has_uniform_machine(self):
        """A shared header is authoritative only when every printed item matches.

        An explicitly cleared row must never appear to inherit a header machine.
        Notes/sections do not have attribution; explicit same-machine overrides
        are safe because this checks the actual stored relation, not its default.
        """
        self.ensure_one()
        items = self._get_order_lines_to_report().filtered(lambda line: not line.display_type)
        return bool(self.x_hm_order_machine_id and items and all(
            line.x_hm_parts_machine_id == self.x_hm_order_machine_id for line in items))

    @api.onchange('x_hm_order_machine_id')
    def _onchange_hm_order_machine(self):
        for order in self:
            for line in order.order_line.filtered('x_hm_use_order_machine'):
                line.x_hm_parts_machine_id = order.x_hm_order_machine_id

    @api.onchange('partner_id', 'company_id')
    def _onchange_hm_machine_customer(self):
        for order in self:
            machine = order.x_hm_order_machine_id
            if machine and (machine.x_company_id != order.company_id or
                            machine.x_partner_id.commercial_partner_id != order.partner_id.commercial_partner_id):
                order.x_hm_order_machine_id = False
                order._onchange_hm_order_machine()

    def _hm_validate_machine(self, machine):
        self.ensure_one()
        if not machine:
            return
        machine.check_access('read')
        error = machine_link_error(
            self.company_id.id, self.partner_id.commercial_partner_id.id,
            machine.x_company_id.id, machine.x_partner_id.commercial_partner_id.id,
            machine.x_retired)
        if error == 'company':
            raise ValidationError(_('Машината трябва да е от фирмата на офертата.'))
        if error == 'customer':
            raise ValidationError(_('Машината трябва да принадлежи на клиента на офертата.'))
        if error == 'retired':
            raise ValidationError(_('Изведена от обслужване машина не може да се избира за оферта.'))

    @api.constrains('x_hm_order_machine_id', 'partner_id', 'company_id')
    def _hm_check_order_machine(self):
        for order in self:
            order._hm_validate_machine(order.x_hm_order_machine_id)

    def write(self, values):
        if 'x_hm_order_machine_id' in values and values.get('order_line'):
            # The web client serializes onchange-updated machines but omits an
            # unchanged True inheritance flag. Recognize only echoes on already
            # inherited, owned lines; do not reinterpret explicit overrides.
            inherited_ids = set(self.order_line.filtered('x_hm_use_order_machine').ids)
            commands = []
            for command in values['order_line']:
                if (command[0] == 1 and command[1] in inherited_ids and
                        'x_hm_use_order_machine' not in command[2] and
                        'x_hm_parts_machine_id' in command[2] and
                        command[2]['x_hm_parts_machine_id'] == values['x_hm_order_machine_id']):
                    command = (1, command[1], dict(command[2], x_hm_use_order_machine=True))
                commands.append(command)
            values = dict(values, order_line=commands)
        result = super().write(values)
        if 'x_hm_order_machine_id' in values:
            for order in self:
                order.order_line.filtered('x_hm_use_order_machine').write({
                    'x_hm_use_order_machine': True,
                    'x_hm_parts_machine_id': order.x_hm_order_machine_id.id})
        if {'partner_id', 'company_id'} & values.keys():
            self.order_line._hm_check_line_machine()
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # False is the upgrade default: existing kit links must remain explicit.
    x_hm_use_order_machine = fields.Boolean(string='От машината на офертата', copy=False)
    x_hm_parts_machine_serial = fields.Char(
        related='x_hm_parts_machine_id.x_serial', string='Сериен № на машина', compute_sudo=False)

    x_hm_parts_history_state = fields.Selection([
        ('offered', 'Предложено'), ('sold', 'Продадено — без доставка'),
        ('part_delivered', 'Частично доставено'), ('delivered', 'Доставено'),
        ('returned', 'Нетно върнато'), ('cancelled', 'Отказано')],
        string='Търговски статус (не монтаж)', compute='_compute_hm_parts_history_state')

    @api.depends('state', 'product_uom_qty', 'qty_delivered')
    def _compute_hm_parts_history_state(self):
        for line in self:
            line.x_hm_parts_history_state = parts_history_state(
                line.state, line.product_uom_qty, line.qty_delivered)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'x_hm_use_order_machine' in fields_list:
            values['x_hm_use_order_machine'] = self.env.context.get(
                'default_x_hm_use_order_machine',
                'default_x_hm_parts_machine_id' not in self.env.context and
                not bool(values.get('x_hm_parts_machine_id')))
        return values

    @api.onchange('order_id', 'x_hm_use_order_machine', 'product_id', 'display_type')
    def _onchange_hm_line_machine(self):
        for line in self:
            if line.display_type:
                line.x_hm_use_order_machine = False
                line.x_hm_parts_machine_id = False
            elif line.x_hm_use_order_machine:
                line.x_hm_parts_machine_id = line.order_id.x_hm_order_machine_id

    @api.constrains('x_hm_parts_machine_id', 'order_id', 'company_id')
    def _hm_check_line_machine(self):
        for line in self:
            line.order_id._hm_validate_machine(line.x_hm_parts_machine_id)

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for values in vals_list:
            values = dict(values)
            if 'order_id' not in values:
                values.update(self.default_get(['order_id']))
            for field_name in ('x_hm_parts_machine_id', 'x_hm_use_order_machine'):
                context_key = 'default_' + field_name
                if field_name not in values and context_key in self.env.context:
                    values[field_name] = self.env.context[context_key]
            order = self.env['sale.order'].browse(values.get('order_id'))
            prepared.append(prepare_line_values(values, order.x_hm_order_machine_id.id))
        return super().create(prepared)

    def write(self, values):
        if {'x_hm_parts_machine_id', 'x_hm_use_order_machine', 'order_id', 'display_type'} & values.keys():
            for line in self:
                order = self.env['sale.order'].browse(values.get('order_id')) if 'order_id' in values else line.order_id
                proposed = dict(values)
                proposed.setdefault('display_type', line.display_type)
                if 'x_hm_parts_machine_id' not in values:
                    proposed.setdefault('x_hm_use_order_machine', line.x_hm_use_order_machine)
                    proposed['x_hm_parts_machine_id'] = line.x_hm_parts_machine_id.id
                prepared = prepare_line_values(proposed, order.x_hm_order_machine_id.id)
                super(SaleOrderLine, line).write(prepared)
            return True
        return super().write(values)
