from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    hm_name_en = fields.Char(
        string="Фирмено име за чужди документи (EN)",
        help="Официалното име на фирмата на латиница, използвано при документи на чужд език.",
    )
    hm_address_en = fields.Text(
        string="Адрес за чужди документи (EN)",
        help="Официалният адрес на латиница, използван при документи на чужд език.",
    )
    hm_mol_bg = fields.Char(
        string="МОЛ / Представляващ",
        help="Име на законния представител/МОЛ, което се отпечатва в българските документи.",
    )
    hm_mol_en = fields.Char(
        string="Представляващ за чужди документи (EN)",
        help="Име на законния представител на латиница за документи на чужд език.",
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    hm_name_en = fields.Char(related="partner_id.hm_name_en", readonly=False)
    hm_address_en = fields.Text(related="partner_id.hm_address_en", readonly=False)
    hm_mol_bg = fields.Char(related="partner_id.hm_mol_bg", readonly=False)
    hm_mol_en = fields.Char(related="partner_id.hm_mol_en", readonly=False)
