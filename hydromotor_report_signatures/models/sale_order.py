from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    hm_available_partner_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_hm_available_partner_bank_ids",
        string="Available Company Bank Accounts",
    )
    hm_partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Банкова сметка за документа",
        default=lambda self: self._default_hm_partner_bank_id(),
        help=(
            "Bank account printed on the quotation/order/pro-forma. "
            "The same account is transferred to invoices created from this sales order."
        ),
    )

    @api.model
    def _default_hm_partner_bank_id(self):
        company = self.env.company
        banks = company.partner_id.bank_ids.filtered(
            lambda bank: not bank.company_id or bank.company_id == company
        )
        return banks[:1]

    @api.depends("company_id")
    def _compute_hm_available_partner_bank_ids(self):
        for order in self:
            company = order.company_id or self.env.company
            order.hm_available_partner_bank_ids = company.partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == company
            )

    @api.onchange("company_id")
    def _onchange_company_id_hm_partner_bank_id(self):
        for order in self:
            available = order.hm_available_partner_bank_ids
            if order.hm_partner_bank_id not in available:
                order.hm_partner_bank_id = available[:1]

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        if self.hm_partner_bank_id:
            values["partner_bank_id"] = self.hm_partner_bank_id.id
        return values
