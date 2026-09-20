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


def patch_code(code):
    if MARKER in code:
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


def post_init_hook(env):
    from odoo.exceptions import UserError
    actions = env['ir.actions.server'].sudo().search([
        ('state', '=', 'code'), ('code', 'ilike', 'def hm_description(')])
    if not actions:
        raise UserError('Не е намерен очакваният конфигуратор. Проверете версията на hydromotor_machine_sales.')
    pending = []
    for action in actions:
        try:
            patched = patch_code(action.code)
        except (ValueError, SyntaxError) as exc:
            raise UserError('Непозната версия на действие %s: %s. Няма приложени промени.' % (action.name, exc)) from exc
        if patched != action.code:
            pending.append((action, action.code, patched))
    params = env['ir.config_parameter'].sudo()
    for action, original, patched in pending:
        params.set_param(PREFIX + str(action.id), json.dumps({'original': original, 'patched': patched}))
        action.write({'code': patched})


def uninstall_hook(env):
    from odoo.exceptions import UserError
    backups = env['ir.config_parameter'].sudo().search([('key', '=like', PREFIX + '%')])
    pending = []
    for row in backups:
        action = env['ir.actions.server'].sudo().browse(int(row.key[len(PREFIX):])).exists()
        saved = json.loads(row.value)
        if action and action.code != saved['patched'] and MARKER in action.code:
            raise UserError('Действие %s е променено след инсталацията. Съгласувайте промените преди деинсталиране.' % action.name)
        if action and action.code == saved['patched']:
            pending.append((action, saved['original']))
    for action, code in pending:
        action.write({'code': code})
    backups.unlink()
