from odoo import _, fields, models
from odoo.exceptions import UserError


class TremolReceiptWizard(models.TransientModel):
    _name = "hydromotor.tremol.receipt.wizard"
    _description = "Confirm TREMOL Fiscal Receipt"

    move_id = fields.Many2one("account.move", required=True, readonly=True)
    partner_id = fields.Many2one(related="move_id.partner_id", readonly=True)
    currency_id = fields.Many2one(related="move_id.currency_id", readonly=True)
    amount_total = fields.Monetary(related="move_id.amount_total", readonly=True)
    payment_method = fields.Selection(
        [("cash", "Cash"), ("card", "Bank card")],
        required=True,
        default="cash",
    )
    confirmation = fields.Boolean(
        string="I confirm that a fiscal receipt must be issued for this payment"
    )

    def action_issue(self):
        self.ensure_one()
        if not self.confirmation:
            raise UserError(_("Confirm the fiscal receipt before continuing."))
        payload = self.move_id._tremol_receipt_payload(self.payment_method)
        return {
            "type": "ir.actions.client",
            "tag": "hydromotor_tremol_fiscal.bridge",
            "params": {"operation": "issue", "payload": payload},
        }

