"""Prevent installing the reconstructed definitions on an unintended Odoo series."""
from odoo import release
from odoo.exceptions import UserError


def pre_init_hook(env):
    if tuple(release.version_info[:2]) != (19, 0):
        raise UserError("This development package targets Odoo 19.0 only. Do not install it on the source SaaS 19.4 database.")
