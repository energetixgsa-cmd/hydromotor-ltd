import re
from decimal import Decimal, ROUND_HALF_UP

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    tremol_fiscal_state = fields.Selection(
        selection=[
            ("not_issued", "Not issued"),
            ("processing", "Processing"),
            ("issued", "Issued"),
            ("error", "Error"),
        ],
        string="Fiscal receipt status",
        default="not_issued",
        copy=False,
        readonly=True,
    )
    tremol_receipt_number = fields.Char(string="Fiscal receipt number", copy=False, readonly=True)
    tremol_fiscal_issued_at = fields.Datetime(string="Issued at", copy=False, readonly=True)
    tremol_last_response = fields.Text(string="Last TREMOL response", copy=False, readonly=True)
    tremol_issue_token = fields.Char(string="Fiscal issue token", copy=False, readonly=True)

    def _tremol_company_config(self):
        self.ensure_one()
        company = self.company_id
        if not company.tremol_enabled:
            raise UserError(_("Enable the TREMOL integration in Settings first."))
        if not company.tremol_server_url or not company.tremol_com_port:
            raise UserError(_("ZFPLabServer address and COM port are required."))
        return {
            "server_url": company.tremol_server_url.rstrip("/") + "/",
            "com_port": company.tremol_com_port.strip().upper(),
            "baud_rate": company.tremol_baud_rate or 0,
            "keep_port_open": bool(company.tremol_keep_port_open),
            "operator_number": company.tremol_operator_number or 1,
            "operator_password": company.tremol_operator_password or "000000",
            "device_number": company.tremol_device_number or "",
            "operator_code": company.tremol_operator_code or "",
            "vat_group": company.tremol_vat_group or "Б",
            "cash_payment_code": company.tremol_cash_payment_code or 0,
            "card_payment_code": company.tremol_card_payment_code or 1,
        }

    def action_tremol_test_connection(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "hydromotor_tremol_fiscal.bridge",
            "params": {
                "operation": "test",
                "move_id": self.id,
                "config": self._tremol_company_config(),
            },
        }

    @api.model
    def tremol_record_test(self, move_id, raw_response):
        move = self.browse(move_id).exists()
        if not move:
            raise UserError(_("Invoice not found."))
        move.company_id.tremol_last_test_at = fields.Datetime.now()
        move.tremol_last_response = raw_response
        return True

    def action_open_tremol_receipt_wizard(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError(_("A fiscal receipt can be issued only for a customer invoice."))
        if self.state != "posted":
            raise UserError(_("Post the invoice before issuing a fiscal receipt."))
        if self.tremol_fiscal_state == "issued":
            raise UserError(_("A fiscal receipt is already recorded for this invoice."))
        if self.tremol_fiscal_state == "processing":
            raise UserError(
                _("A fiscal operation is already in progress. Check the device before retrying.")
            )
        if self.payment_state not in ("paid", "in_payment"):
            raise UserError(_("Register the invoice payment before issuing a fiscal receipt."))
        if not self.company_id.tremol_last_test_at:
            raise UserError(_("Run 'Test TREMOL connection' successfully first."))
        if self.currency_id != self.company_currency_id:
            raise UserError(_("The invoice currency must match the company currency."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "hydromotor.tremol.receipt.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def _tremol_receipt_payload(self, payment_method):
        self.ensure_one()
        if self.tremol_fiscal_state in ("processing", "issued"):
            raise UserError(_("This invoice cannot start another fiscal operation."))
        config = self._tremol_company_config()
        commercial_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.quantity
        )
        if not commercial_lines:
            raise UserError(_("The invoice has no fiscal receipt lines."))

        items = []
        device_total = Decimal("0")
        for line in commercial_lines:
            quantity = Decimal(str(abs(line.quantity)))
            unit_price_included = (Decimal(str(abs(line.price_total))) / quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            name = re.sub(r"[|\r\n]+", " ", line.name or line.product_id.display_name)
            items.append(
                {
                    "name": name[:36],
                    "vat_group": config["vat_group"],
                    "price": f"{unit_price_included:.2f}",
                    "quantity": f"{quantity:.3f}".rstrip("0").rstrip("."),
                }
            )
            device_total += unit_price_included * quantity

        invoice_total = Decimal(str(abs(self.amount_total))).quantize(Decimal("0.01"))
        rounding_difference = (invoice_total - device_total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if rounding_difference:
            items.append(
                {
                    "name": _("Rounding adjustment"),
                    "vat_group": config["vat_group"],
                    "price": f"{rounding_difference:.2f}",
                    "quantity": "1",
                }
            )

        # The URN must be unique, 24 characters maximum and stable for retries.
        # Its final legal format must be confirmed with the fiscal-service technician.
        token = self.tremol_issue_token or (
            f"{config['device_number']}-{config['operator_code']}-{self.id:07d}"
        )
        if not self.tremol_issue_token:
            self.tremol_issue_token = token
        self.tremol_fiscal_state = "processing"

        payment_code = (
            config["cash_payment_code"]
            if payment_method == "cash"
            else config["card_payment_code"]
        )
        return {
            "move_id": self.id,
            "invoice_name": self.name,
            "currency": self.currency_id.name,
            "amount_total": f"{abs(self.amount_total):.2f}",
            "payment_method": payment_method,
            "payment_code": payment_code,
            "unique_receipt_number": token,
            "items": items,
            "config": config,
        }

    def action_tremol_allow_retry(self):
        for move in self:
            if move.tremol_fiscal_state == "issued":
                raise UserError(_("An issued fiscal receipt cannot be reset."))
            move.write({"tremol_fiscal_state": "not_issued"})
            move.message_post(
                body=_(
                    "TREMOL retry was enabled manually. The operator must first verify that no receipt was issued."
                )
            )
        return True

    @api.model
    def tremol_record_result(self, move_id, success, raw_response, receipt_number=False):
        move = self.browse(move_id).exists()
        if not move:
            raise UserError(_("Invoice not found."))
        values = {
            "tremol_last_response": raw_response,
            "tremol_fiscal_state": "issued" if success else "error",
        }
        if success:
            values.update(
                {
                    "tremol_fiscal_issued_at": fields.Datetime.now(),
                    "tremol_receipt_number": receipt_number or move.tremol_issue_token,
                }
            )
        move.write(values)
        body = (
            _("TREMOL fiscal receipt issued: %s") % values.get("tremol_receipt_number")
            if success
            else _("TREMOL fiscal operation failed. Review the saved response before retrying.")
        )
        move.message_post(body=body)
        return True
