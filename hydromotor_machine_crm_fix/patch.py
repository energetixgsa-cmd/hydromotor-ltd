"""Patch only the CRM guard, preserving bilingual descriptions and other code."""
from odoo import api, models
from odoo.exceptions import UserError

OLD = """    if order.opportunity_id != cfg.x_lead_id:
        raise UserError('Изберете същата CRM възможност като в офертата.')
"""
MARKER = '# HM_CRM_LINK_FIX_V1'
NEW = """    # HM_CRM_LINK_FIX_V1
    if order.opportunity_id and cfg.x_lead_id and order.opportunity_id != cfg.x_lead_id:
        raise UserError('Офертата %s е свързана с CRM възможност „%s“, а конфигурацията — с „%s“. Изберете една и съща възможност в двата записа.' % (order.name, order.opportunity_id.display_name, cfg.x_lead_id.display_name))
    crm_lead = order.opportunity_id or cfg.x_lead_id
    if crm_lead:
        if crm_lead.company_id and crm_lead.company_id != order.company_id:
            raise UserError('CRM възможността е за друго дружество.')
        if crm_lead.partner_id and crm_lead.partner_id.commercial_partner_id != order.partner_id.commercial_partner_id:
            raise UserError('CRM възможността е за друг клиент. Проверете клиента на възможността и офертата.')
        if not order.opportunity_id:
            order.write({'opportunity_id': crm_lead.id})
        if not cfg.x_lead_id:
            cfg.write({'x_lead_id': crm_lead.id})
    # END_HM_CRM_LINK_FIX_V1
"""


def patch_code(code):
    if MARKER in code:
        if code.count(NEW) != 1:
            raise UserError('CRM поправката е редактирана. Нужна е проверка на действието.')
        return code
    if code.count(OLD) != 1:
        raise UserError('Непозната версия на CRM проверката. Не са приложени промени.')
    result = code.replace(OLD, NEW, 1)
    compile(result, '<hydromotor-crm-fix>', 'exec')
    return result


class MachineCRMPatch(models.AbstractModel):
    _name = 'hydromotor.machine.crm.patch'
    _description = 'Hydromotor CRM action patch'

    @api.model
    def apply_patch(self):
        if not self.env.su and not self.env.user.has_group('base.group_system'):
            raise UserError('Нужни са администраторски права.')
        refs = self.env['ir.model.data'].sudo().search([
            ('module', '=', 'hydromotor_machine_sales'),
            ('model', '=', 'ir.actions.server'),
        ])
        actions = self.env['ir.actions.server'].sudo().browse(refs.mapped('res_id')).exists()
        actions = actions.filtered(lambda a: a.state == 'code' and 'def hm_publish(' in (a.code or ''))
        if not actions:
            raise UserError('Не са намерени действията на конфигуратора Hydromotor.')
        pending = [(action, patch_code(action.code)) for action in actions]
        for action, code in pending:
            if action.code != code:
                action.write({'code': code})
        return True


def uninstall_hook(env):
    actions = env['ir.actions.server'].sudo().search([('state', '=', 'code'), ('code', 'ilike', MARKER)])
    pending = []
    for action in actions:
        if action.code.count(NEW) != 1:
            raise UserError('CRM поправката в %s е редактирана. Проверете я преди деинсталиране.' % action.name)
        pending.append((action, action.code.replace(NEW, OLD, 1)))
    for action, code in pending:
        action.write({'code': code})
