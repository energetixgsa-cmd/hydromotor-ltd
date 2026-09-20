from odoo import api, models
from odoo.exceptions import UserError
from .hooks import apply_patches


class HydromotorBilingualPatch(models.AbstractModel):
    _name = 'hydromotor.machine.bilingual.patch'
    _description = 'Hydromotor bilingual and CRM update'

    @api.model
    def apply_patch(self):
        if not self.env.su and not self.env.user.has_group('base.group_system'):
            raise UserError('Нужни са администраторски права.')
        apply_patches(self.env)
        return True
