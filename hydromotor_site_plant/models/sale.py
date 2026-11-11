from odoo import api, fields, models
from odoo.exceptions import ValidationError


TARGETS = {'hm_target_project_id', 'hm_target_plant_id'}


def validate_target(record):
    project, plant = record.hm_target_project_id, record.hm_target_plant_id
    project.check_access('read')
    plant.check_access('read')
    if project and (project.company_id != record.company_id or record.company_id not in record.env.companies):
        raise ValidationError('Planned site must belong to the document company and allowed companies.')
    if plant and (not project or plant.project_id != project or plant.company_id != record.company_id):
        raise ValidationError('Planned plant must belong to the planned site and document company.')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    hm_current_site_id = fields.Many2one('project.project', string='Текущ обект на машината', compute='_compute_hm_current_site_and_plant', store=False, compute_sudo=False)
    hm_current_plant_id = fields.Many2one('hm.concrete.plant', string='Текущ бетонов възел', compute='_compute_hm_current_site_and_plant', store=False, compute_sudo=False)

    @api.depends('x_hm_order_machine_id')
    def _compute_hm_current_site_and_plant(self):
        """Compute both site and plant in ONE pass to avoid circular deps."""
        for record in self:
            machine = record.x_hm_order_machine_id
            current_site = False
            current_plant = False
            if machine:
                assignments = machine.x_hm_assignment_ids
                current = assignments.filtered(lambda a: not a.ended_at)[:1]
                current_site = current.project_id if current else False
                current_plant = current.plant_id if current else False
            record.hm_current_site_id = current_site
            record.hm_current_plant_id = current_plant

    hm_target_project_id = fields.Many2one('project.project', string='Planned site / Project', check_company=True, copy=False, ondelete='restrict', index=True,
        help='Commercial destination only. Quotation, sale and delivery do not prove installation.')
    hm_target_plant_id = fields.Many2one('hm.concrete.plant', string='Planned concrete plant', check_company=True, copy=False, ondelete='restrict', index=True)

    @api.constrains('hm_target_project_id', 'hm_target_plant_id', 'company_id')
    def _validate_hm_target(self):
        for record in self:
            validate_target(record)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            validate_target(self.new(vals))
        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            if TARGETS & vals.keys() or 'company_id' in vals:
                validate_target(self.new({
                    'company_id': vals.get('company_id', record.company_id.id),
                    **{k: vals.get(k, record[k].id) for k in TARGETS}}))
        result = super().write(vals)
        if TARGETS & vals.keys():
            self.order_line.filtered('hm_use_order_target')._apply_order_target()
        return result

    @api.onchange('hm_target_project_id')
    def _onchange_hm_site(self):
        if self.hm_target_plant_id.project_id != self.hm_target_project_id:
            self.hm_target_plant_id = False

    @api.onchange('hm_target_project_id', 'hm_target_plant_id')
    def _onchange_hm_targets(self):
        for line in self.order_line.filtered('hm_use_order_target'):
            line.hm_target_project_id = self.hm_target_project_id
            line.hm_target_plant_id = self.hm_target_plant_id


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    hm_part_code = fields.Char(related='product_id.default_code', string='Код на частта', compute_sudo=False)

    hm_current_site_id = fields.Many2one('project.project', string='Текущ обект на машината', compute='_compute_hm_current_site_and_plant', store=False, compute_sudo=False)
    hm_current_plant_id = fields.Many2one('hm.concrete.plant', string='Текущ бетонов възел', compute='_compute_hm_current_site_and_plant', store=False, compute_sudo=False)

    @api.depends('x_hm_parts_machine_id')
    def _compute_hm_current_site_and_plant(self):
        """Compute both site and plant in ONE pass to avoid circular deps."""
        for record in self:
            machine = record.x_hm_parts_machine_id
            current_site = False
            current_plant = False
            if machine:
                assignments = machine.x_hm_assignment_ids
                current = assignments.filtered(lambda a: not a.ended_at)[:1]
                current_site = current.project_id if current else False
                current_plant = current.plant_id if current else False
            record.hm_current_site_id = current_site
            record.hm_current_plant_id = current_plant

    hm_use_order_target = fields.Boolean(string='Use order planned destination', default=True, copy=False)
    hm_target_project_id = fields.Many2one('project.project', string='Planned site / Project', check_company=True, copy=False, ondelete='restrict', index=True)
    hm_target_plant_id = fields.Many2one('hm.concrete.plant', string='Planned concrete plant', check_company=True, copy=False, ondelete='restrict', index=True)

    @api.constrains('hm_target_project_id', 'hm_target_plant_id', 'company_id', 'display_type')
    def _validate_hm_target(self):
        for record in self:
            validate_target(record)
            if record.display_type and (record.hm_target_project_id or record.hm_target_plant_id):
                raise ValidationError('Sections and notes cannot carry a planned destination.')

    def _apply_order_target(self):
        for line in self:
            super(SaleOrderLine, line).write({
                'hm_target_project_id': line.order_id.hm_target_project_id.id if not line.display_type else False,
                'hm_target_plant_id': line.order_id.hm_target_plant_id.id if not line.display_type else False})

    @api.model_create_multi
    def create(self, vals_list):
        values = []
        for incoming in vals_list:
            vals = dict(incoming)
            inherit = vals.get('hm_use_order_target', not bool(TARGETS & vals.keys()))
            vals['hm_use_order_target'] = inherit
            if inherit:
                order = self.env['sale.order'].browse(vals.get('order_id'))
                vals.update({
                    'hm_target_project_id': order.hm_target_project_id.id if not vals.get('display_type') else False,
                    'hm_target_plant_id': order.hm_target_plant_id.id if not vals.get('display_type') else False})
            validate_target(self.new(vals))
            values.append(vals)
        return super().create(values)

    def write(self, vals):
        for line in self:
            incoming = dict(vals)
            if TARGETS & incoming.keys() and 'hm_use_order_target' not in incoming:
                # Preserve inherited flags on unchanged onchange/web_save echoes.
                echo = line.hm_use_order_target and all(incoming[k] == line.order_id[k].id for k in TARGETS & incoming.keys())
                if not echo:
                    incoming['hm_use_order_target'] = False
            if TARGETS & incoming.keys() or 'order_id' in incoming:
                validate_target(self.new({
                    'order_id': incoming.get('order_id', line.order_id.id),
                    **{k: incoming.get(k, line[k].id) for k in TARGETS}}))
            super(SaleOrderLine, line).write(incoming)
            if incoming.get('hm_use_order_target') or ('order_id' in incoming and line.hm_use_order_target):
                line._apply_order_target()
        return True

    @api.onchange('hm_use_order_target')
    def _onchange_hm_inherit(self):
        if self.hm_use_order_target:
            self.hm_target_project_id = self.order_id.hm_target_project_id
            self.hm_target_plant_id = self.order_id.hm_target_plant_id

    @api.onchange('hm_target_project_id')
    def _onchange_hm_site(self):
        if self.hm_target_plant_id.project_id != self.hm_target_project_id:
            self.hm_target_plant_id = False
