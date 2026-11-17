from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from ..helpers import canonical_snapshot, validate_signature


class Signing(models.Model):
    _name = 'hm.service.signing'
    _description = 'Service signing snapshot'
    _rec_name = 'job_id'

    job_id = fields.Many2one('x_hm_job', required=True, ondelete='restrict', copy=False)
    company_id = fields.Many2one(related='job_id.x_company_id', store=True)
    snapshot_json = fields.Text(readonly=True, copy=False)
    snapshot_hash = fields.Char(readonly=True, copy=False)
    technician_name = fields.Char(copy=False)
    technician_signature = fields.Binary(attachment=False, copy=False)
    technician_signed_at = fields.Datetime(readonly=True, copy=False)
    technician_user_id = fields.Many2one('res.users', readonly=True, copy=False)
    customer_name = fields.Char(copy=False)
    customer_title = fields.Char(copy=False)
    customer_signature = fields.Binary(attachment=False, copy=False)
    customer_signed_at = fields.Datetime(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        protected = {'snapshot_json', 'snapshot_hash', 'technician_signed_at',
                     'customer_signed_at', 'technician_user_id', 'company_id'}
        prepared = []
        for original in vals_list:
            vals = dict(original)
            if protected.intersection(vals):
                raise ValidationError(_('Server-owned fields cannot be supplied.'))
            job = self.env['x_hm_job'].browse(vals.get('job_id')).exists()
            job.ensure_one()
            job.check_access('read')
            if job.x_company_id not in self.env.companies:
                raise AccessError(_('Company not allowed.'))
            data = {name: job[name] or '' for name in (
                'x_reference', 'x_name', 'x_problem', 'x_diagnosis', 'x_work_done')}
            data.update(labor_hours=job.x_labor_hours, travel_km=job.x_travel_km,
                        customer=job.x_partner_id.display_name,
                        machine=job.x_machine_id.x_name,
                        serial=job.x_machine_id.x_serial or '')
            vals['snapshot_json'], vals['snapshot_hash'] = canonical_snapshot(data)
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        if {'snapshot_json', 'snapshot_hash', 'job_id', 'company_id',
            'technician_signed_at', 'customer_signed_at', 'technician_user_id'}.intersection(vals):
            raise ValidationError(_('Server-owned fields cannot be changed.'))
        for record in self:
            for role in ('technician', 'customer'):
                protected = {role + '_name', role + '_signature'}
                if role == 'customer':
                    protected.add('customer_title')
                if record[role + '_signed_at'] and protected.intersection(vals):
                    raise ValidationError(_('A sealed signature cannot be changed.'))
        return super().write(vals)

    def _seal(self, role):
        self.ensure_one()
        self.check_access('write')
        self.job_id.check_access('read')
        if not self.env.user.has_group('hydromotor_service.group_service_user'):
            raise AccessError(_('Service access required.'))
        if role == 'technician' and self.job_id.x_technician_id != self.env.user and not self.env.user.has_group('hydromotor_service.group_service_manager'):
            raise AccessError(_('Only the assigned technician or service manager may sign.'))
        if self[role + '_signed_at']:
            raise ValidationError(_('Already signed.'))
        if not (self[role + '_name'] or '').strip():
            raise ValidationError(_('Signer name is required.'))
        try:
            validate_signature(self[role + '_signature'])
        except ValueError as exc:
            raise ValidationError(_('A valid nonblank PNG signature is required.')) from exc
        # Force a row revision before sealing; concurrent stale transactions must retry
        # as a whole rather than overwrite an already committed signature.
        super(Signing, self).write({'snapshot_hash': self.snapshot_hash})
        self.flush_recordset()
        values = {role + '_signed_at': fields.Datetime.now()}
        if role == 'technician':
            values['technician_user_id'] = self.env.uid
        return super(Signing, self).write(values)

    def action_seal_technician(self):
        return self._seal('technician')

    def action_seal_customer(self):
        return self._seal('customer')

    def unlink(self):
        if any(r.technician_signed_at or r.customer_signed_at for r in self):
            raise ValidationError(_('Signed snapshots cannot be deleted.'))
        return super().unlink()
