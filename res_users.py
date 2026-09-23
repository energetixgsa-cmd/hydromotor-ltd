from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    invoice_name_bg = fields.Char(
        string="Име за документи (BG)",
        help="Bulgarian name printed in the Prepared by section of outgoing invoices.",
    )
    invoice_name_en = fields.Char(
        string="Document name (EN)",
        help="English/Latin name printed in the Prepared by section of outgoing invoices.",
    )
