# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    hm_report_name_bg = fields.Char(
        string="Document Name (Bulgarian)",
        help="Name shown for this user on Bulgarian customer documents.",
    )
    hm_report_name_en = fields.Char(
        string="Document Name (English)",
        help="Name shown for this user on non-Bulgarian customer documents.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["hm_report_name_bg", "hm_report_name_en"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["hm_report_name_bg", "hm_report_name_en"]

    def _hm_report_name(self, lang_code=None):
        """Return the document-facing user name for the requested language.

        Bulgarian documents use hm_report_name_bg. All other languages use
        hm_report_name_en. The normal Odoo user name is always the fallback.
        """
        self.ensure_one()
        lang = (lang_code or self.env.context.get("lang") or "").lower()
        if lang.startswith("bg"):
            return self.hm_report_name_bg or self.name
        return self.hm_report_name_en or self.name

    @api.depends("name", "hm_report_name_bg", "hm_report_name_en")
    @api.depends_context("lang", "hm_bilingual_report_name")
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("hm_bilingual_report_name"):
            return
        lang = self.env.context.get("lang")
        for user in self:
            user.display_name = user._hm_report_name(lang)

