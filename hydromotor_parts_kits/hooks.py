from odoo import release
from odoo.exceptions import UserError


def pre_init_hook(env):
    if tuple(release.version_info[:2]) != (19, 0):
        raise UserError("Hydromotor Parts Kits targets Odoo 19.0 only.")
