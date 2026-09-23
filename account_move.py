from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        self.ensure_one()
        fiscal_country = self.company_id.account_fiscal_country_id or self.company_id.country_id
        if self.move_type == "out_invoice" and fiscal_country.code == "BG":
            return "hydromotor_report_signatures.report_customer_invoice_document"
        return super()._get_name_invoice_report()
