"""Narrow, transactional patch for recovered XML-defined server actions.

Does not load catalogues, change prices or modify existing quotation snapshots.
Unrecognized action layouts stop installation rather than guessing.
"""
import ast
import json

MARKER = '# HM_BILINGUAL_2026_V1'
PREFIX = 'hydromotor_machine_bilingual.backup.'
INSERT = '''    # HM_BILINGUAL_2026_V1
    base_name = (cfg.x_base_id.x_name_en or cfg.x_base_id.x_name) if en else cfg.x_base_id.x_name
    brand = 'KEMROC' if 'KEMROC' in (cfg.x_base_id.x_family or '').upper() else 'Putzmeister'
    title = base_name if base_name.upper().startswith(brand.upper()) else brand + ' ' + base_name
    out = [title, ('Manufacturer code: ' if en else 'Производителски код: ') + cfg.x_base_id.x_code, '']
    standard = (cfg.x_base_id.x_standard_text_en or '') if en else (cfg.x_base_id.x_standard_text or '')
    if standard:
        out += [('Base standard equipment (before selected changes):' if en else 'Стандартно оборудване на базата (преди избраните промени):'), standard, '']
'''


def patch_bilingual(code):
    if MARKER in code:
        if code.count(INSERT) != 1:
            raise ValueError("Edited bilingual header; review before upgrading")
        return code
    tree = ast.parse(code)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'hm_description']
    if len(functions) != 1:
        raise ValueError('Expected exactly one hm_description function')
    function = functions[0]
    outputs = [n for n in function.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'out' for t in n.targets)]
    if len(outputs) != 1 or not isinstance(outputs[0].value, ast.List):
        raise ValueError('Unrecognized quotation description layout')
    target = outputs[0]
    first = function.body[0]
    if not (isinstance(first, ast.Assign) and ast.unparse(first) == "en = cfg.x_language == 'en'"):
        raise ValueError('Unrecognized language selection')
    if len(target.value.elts) != 3 or 'x_base_id.x_code' not in ast.unparse(target):
        raise ValueError('Unrecognized quotation header; review current module')
    lines = code.splitlines(keepends=True)
    lines[target.lineno-1:target.end_lineno] = [INSERT]
    patched = ''.join(lines)
    patched = patched.replace("review_note=opt.x_review_note or ''", "review_note=((opt.x_review_note_en or '') if cfg.x_language == 'en' else (opt.x_review_note or ''))")
    compile(patched, '<bilingual-server-action>', 'exec')
    return patched


CRM_OLD = "    if order.opportunity_id != cfg.x_lead_id:\n        raise UserError('Изберете същата CRM възможност като в офертата.')\n"
CRM_NEW = "    # HM_CRM_LINK_FIX_V1\n    if order.opportunity_id and cfg.x_lead_id and order.opportunity_id != cfg.x_lead_id:\n        raise UserError('Офертата %s е свързана с CRM възможност „%s“, а конфигурацията — с „%s“. Изберете една и съща възможност в двата записа.' % (order.name, order.opportunity_id.display_name, cfg.x_lead_id.display_name))\n    crm_lead = order.opportunity_id or cfg.x_lead_id\n    if crm_lead:\n        if crm_lead.company_id and crm_lead.company_id != order.company_id:\n            raise UserError('CRM възможността е за друго дружество.')\n        if crm_lead.partner_id and crm_lead.partner_id.commercial_partner_id != order.partner_id.commercial_partner_id:\n            raise UserError('CRM възможността е за друг клиент. Проверете клиента на възможността и офертата.')\n        if not order.opportunity_id:\n            order.write({'opportunity_id': crm_lead.id})\n        if not cfg.x_lead_id:\n            cfg.write({'x_lead_id': crm_lead.id})\n    # END_HM_CRM_LINK_FIX_V1\n"
CRM_MARKER = '# HM_CRM_LINK_FIX_V1'


def patch_code(code):
    patched = patch_bilingual(code)
    if CRM_MARKER in patched:
        if patched.count(CRM_NEW) != 1:
            raise ValueError('Edited CRM patch; review before upgrading')
    else:
        if patched.count(CRM_OLD) != 1:
            raise ValueError('Unrecognized CRM guard')
        patched = patched.replace(CRM_OLD, CRM_NEW, 1)
    compile(patched, '<hydromotor-bilingual-crm>', 'exec')
    return patched


def prepare_backup(code, saved=None):
    patched = patch_code(code)
    if MARKER in code:
        if not saved or code != saved.get('patched'):
            raise ValueError('Existing bilingual code differs from its backup; review required')
        original = saved['original']
    else:
        original = code
    if MARKER in original or CRM_MARKER in original:
        raise ValueError('Backup contains another patch; remove the separate CRM fix first')
    return {'original': original, 'patched': patched}


def apply_patches(env):
    from odoo.exceptions import UserError
    if env['ir.module.module'].sudo().search_count([
        ('name', '=', 'hydromotor_machine_crm_fix'),
        ('state', 'in', ['installed', 'to upgrade', 'to install', 'to remove'])]):
        raise UserError('Първо деинсталирайте отделния Hydromotor Machine CRM Link Fix. Поправката вече е включена в двуезичния модул.')
    refs = env['ir.model.data'].sudo().search([
        ('module', '=', 'hydromotor_machine_sales'), ('model', '=', 'ir.actions.server')])
    actions = env['ir.actions.server'].sudo().browse(refs.mapped('res_id')).exists()
    actions = actions.filtered(lambda a: a.state == 'code' and 'def hm_description(' in (a.code or ''))
    if not actions:
        raise UserError('Не са намерени действията на конфигуратора Hydromotor.')
    params = env['ir.config_parameter'].sudo()
    pending = []
    for action in actions:
        try:
            raw = params.get_param(PREFIX + str(action.id))
            saved = json.loads(raw) if raw else None
            backup = prepare_backup(action.code, saved)
        except (ValueError, SyntaxError, KeyError, TypeError) as exc:
            raise UserError('Не може да се обнови действие %s: %s. Промените са отменени.' % (action.name, exc)) from exc
        pending.append((action, backup))
    for action, backup in pending:
        params.set_param(PREFIX + str(action.id), json.dumps(backup))
        if action.code != backup['patched']:
            action.write({'code': backup['patched']})


def post_init_hook(env):
    apply_patches(env)


def uninstall_hook(env):
    from odoo.exceptions import UserError
    rows = env['ir.config_parameter'].sudo().search([('key', '=like', PREFIX + '%')])
    pending = []
    for row in rows:
        action = env['ir.actions.server'].sudo().browse(int(row.key[len(PREFIX):])).exists()
        saved = json.loads(row.value)
        if action and action.code != saved['patched'] and (MARKER in action.code or CRM_MARKER in action.code):
            raise UserError('Действие %s е променено. Проверете кода преди деинсталиране.' % action.name)
        if action and action.code == saved['patched']:
            pending.append((action, saved['original']))
    for action, code in pending:
        action.write({'code': code})
    rows.unlink()
