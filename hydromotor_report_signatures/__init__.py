from . import models


def post_init_hook(env):
    """Seed the known Hydromotor bilingual report name without changing the Odoo login/name."""
    users = env["res.users"].with_context(active_test=False).search([
        ("name", "ilike", "Georgi Aenski"),
    ])
    for user in users:
        values = {}
        if not user.invoice_name_bg:
            values["invoice_name_bg"] = "Георги Аенски"
        if not user.invoice_name_en:
            values["invoice_name_en"] = "Georgi Aenski"
        if values:
            user.write(values)
