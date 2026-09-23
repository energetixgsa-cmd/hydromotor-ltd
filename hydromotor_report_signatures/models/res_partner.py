from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    hm_name_en = fields.Char(
        string="Legal name (EN)",
        help="English/Latin legal name used on customer-facing documents for foreign partners.",
    )
    hm_address_en = fields.Text(
        string="Legal address (EN)",
        help="English/Latin legal address used on customer-facing documents for foreign partners.",
    )
    hm_mol_bg = fields.Char(
        string="МОЛ / Представляващ",
        help="Bulgarian name of the legal representative / materially responsible person printed on documents.",
    )
    hm_mol_en = fields.Char(
        string="Legal representative (EN)",
        help="English/Latin name of the legal representative printed on foreign-language documents.",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    hm_name_en = fields.Char(related="partner_id.hm_name_en", readonly=False)
    hm_address_en = fields.Text(related="partner_id.hm_address_en", readonly=False)
    hm_mol_bg = fields.Char(related="partner_id.hm_mol_bg", readonly=False)
    hm_mol_en = fields.Char(related="partner_id.hm_mol_en", readonly=False)
