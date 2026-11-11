from uuid import uuid4
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from ..schema import install_scope



class ConcretePlant(models.Model):
    _name = 'hm.concrete.plant'
    _description = 'Concrete batching plant installation (not a machine component)'
    _check_company_auto = True

    name = fields.Char(required=True)
    owner_id = fields.Many2one('res.partner', string='Plant owner', ondelete='restrict')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    project_id = fields.Many2one('project.project', string='Site / Project', required=True, check_company=True, ondelete='restrict')
    assignment_ids = fields.One2many('hm.machine.assignment', 'plant_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.new(vals)._validate_scope()
        return super().create(vals_list)

    @api.constrains('company_id', 'project_id')
    def _validate_scope(self):
        for record in self:
            record.project_id.check_access('read')
            if record.project_id.company_id != record.company_id or record.company_id not in self.env.companies:
                raise ValidationError('Plant and site must have the same allowed, explicit company.')

    def write(self, vals):
        self.check_access('write')
        if {'project_id', 'company_id'} & vals.keys():
            # Narrow referential-integrity guard, including inaccessible rows.
            # Only existence is checked; no business data is returned to caller.
            for record in self:
                if any(vals.get(k, record[k].id) != record[k].id for k in ('project_id', 'company_id')):
                    self.env.cr.execute("SELECT 1 FROM hm_machine_assignment WHERE plant_id=%s UNION ALL SELECT 1 FROM sale_order WHERE hm_target_plant_id=%s UNION ALL SELECT 1 FROM sale_order_line WHERE hm_target_plant_id=%s LIMIT 1", [record.id, record.id, record.id])
                    if self.env.cr.fetchone():
                        raise ValidationError('Referenced plant site/company is immutable; create another installation.')
        return super().write(vals)


class ProjectSite(models.Model):
    _inherit = 'project.project'

    hm_plant_ids = fields.One2many('hm.concrete.plant', 'project_id', string='Concrete plants')
    hm_assignment_ids = fields.One2many('hm.machine.assignment', 'project_id', string='Actual assignment history', readonly=True)

    def write(self, vals):
        self.check_access('write')
        if 'company_id' in vals:
            for record in self:
                if vals['company_id'] != record.company_id.id:
                    self.env.cr.execute("SELECT 1 FROM hm_machine_assignment WHERE project_id=%s UNION ALL SELECT 1 FROM hm_concrete_plant WHERE project_id=%s UNION ALL SELECT 1 FROM sale_order WHERE hm_target_project_id=%s UNION ALL SELECT 1 FROM sale_order_line WHERE hm_target_project_id=%s LIMIT 1", [record.id, record.id, record.id, record.id])
                    if self.env.cr.fetchone():
                        raise ValidationError('Site company cannot change while referenced by a plant or assignment.')
        return super().write(vals)


class MachineAssignment(models.Model):
    _name = 'hm.machine.assignment'
    _description = 'Actual machine site assignment history'
    _order = 'started_at desc, id desc'
    _check_company_auto = True

    machine_id = fields.Many2one('x_hm_machine', required=True, ondelete='restrict', index=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, ondelete='restrict')
    project_id = fields.Many2one('project.project', string='Actual site / Project', required=True, check_company=True, ondelete='restrict', index=True)
    plant_id = fields.Many2one('hm.concrete.plant', string='Actual concrete plant', check_company=True, ondelete='restrict', index=True)
    started_at = fields.Datetime(required=True, default=fields.Datetime.now, copy=False)
    ended_at = fields.Datetime(copy=False)
    note = fields.Text()
    request_key = fields.Char(required=True, default=lambda self: str(uuid4()), copy=False, index=True)

    _request_unique = models.Constraint('UNIQUE(machine_id, request_key)', 'Assignment request already processed.')
    _time_order = models.Constraint('CHECK(ended_at IS NULL OR ended_at >= started_at)', 'End precedes start.')

    def init(self):
        # Odoo 19 initializes _auto_init/init per model, not all tables first.
        # Queue cross-model FK DDL until every model's columns exist.
        self.pool.post_init(install_scope, self.env.cr)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS hm_assignment_one_open ON hm_machine_assignment (machine_id) WHERE ended_at IS NULL")

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.plant_id.project_id != self.project_id:
            self.plant_id = False

    @api.onchange('machine_id')
    def _onchange_machine(self):
        if self.machine_id:
            self.company_id = self.machine_id.x_company_id

    def _lock_machine(self, machine):
        # Real UPDATE + flush serializes concurrent writers under Odoo's
        # REPEATABLE READ isolation. A conflicting worker must retry its WHOLE
        # transaction (standard Odoo request retry), not just re-search.
        machine.check_access('write')
        machine.write({'x_hm_assignment_revision': machine.x_hm_assignment_revision + 1})
        machine.flush_recordset(['x_hm_assignment_revision'])

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access('create')
        with self.env.cr.savepoint():
            return self._create_commands(vals_list)

    def _create_commands(self, vals_list):
        result = [None] * len(vals_list)
        # Stable order prevents lock-order inversions for a multi-create.
        for index, vals in sorted(enumerate(vals_list), key=lambda pair: pair[1].get('machine_id', 0)):
            vals = dict(vals)
            if any(k in vals for k in ('started_at', 'ended_at', 'create_uid', 'create_date', 'write_uid', 'write_date')):
                raise ValidationError('Assignment timestamps and actors are server-controlled.')
            machine = self.env['x_hm_machine'].browse(vals.get('machine_id')).exists()
            if not machine:
                raise ValidationError('Select an existing machine.')
            machine.ensure_one()
            self._lock_machine(machine)
            key = vals.setdefault('request_key', str(uuid4()))
            if not key or len(key) > 128:
                raise ValidationError('A nonempty request key up to 128 characters is required.')
            previous = self.search([('machine_id', '=', machine.id), ('request_key', '=', key)], limit=1)
            if previous:
                if (previous.project_id.id != vals.get('project_id') or previous.plant_id.id != (vals.get('plant_id') or False)
                        or previous.note != (vals.get('note') or False)):
                    raise ValidationError('Request key reused with different assignment details.')
                result[index] = previous.id
                continue
            project = self.env['project.project'].browse(vals.get('project_id')).exists()
            plant = self.env['hm.concrete.plant'].browse(vals.get('plant_id')).exists()
            project.check_access('read')
            plant.check_access('read')
            company = machine.x_company_id
            if (not project or not project.active or company not in self.env.companies
                    or project.company_id != company or vals.get('company_id', company.id) != company.id):
                raise ValidationError('Machine and active site must share one allowed explicit company.')
            if plant and (plant.project_id != project or plant.company_id != company or not plant.active):
                raise ValidationError('Concrete plant must belong to the selected active site and company.')
            vals['company_id'] = company.id
            now = fields.Datetime.now()
            current = self.search([('machine_id', '=', machine.id), ('ended_at', '=', False)])
            if current:
                super(MachineAssignment, current).write({'ended_at': now})
                current.flush_recordset(['ended_at'])
            vals['started_at'] = now
            result[index] = super().create([vals]).id
        self._invalidate_sale_locations()
        return self.browse(result)

    def _invalidate_sale_locations(self):
        # Nonstored sale computes cannot declare XML-only paths at bootstrap.
        # Invalidate the environment cache without searching/elevating sale records.
        for model in ('sale.order', 'sale.order.line'):
            self.env[model].invalidate_model(['hm_current_site_id', 'hm_current_plant_id'])

    def write(self, vals):
        raise ValidationError('Assignment history is immutable. Record a new assignment or end the current one.')

    def unlink(self):
        raise ValidationError('Assignment history cannot be deleted.')

    def action_end(self):
        self.check_access('write')
        for record in self.sorted('machine_id'):
            self._lock_machine(record.machine_id)
            record.invalidate_recordset(['ended_at'])
            if not record.ended_at:
                super(MachineAssignment, record).write({'ended_at': fields.Datetime.now()})
        self._invalidate_sale_locations()
        return True

