import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    tremol_enabled = fields.Boolean(string="TREMOL integration enabled", default=False)
    tremol_server_url = fields.Char(
        string="ZFPLabServer address",
        default="http://127.0.0.1:4444/",
    )
    tremol_com_port = fields.Char(string="COM port", default="COM4")
    tremol_baud_rate = fields.Integer(string="Baud rate", default=0)
    tremol_keep_port_open = fields.Boolean(string="Keep port open", default=True)
    tremol_operator_number = fields.Integer(string="Operator number", default=1)
    tremol_operator_password = fields.Char(string="Operator password", default="000000")
    tremol_device_number = fields.Char(string="Fiscal device number", default="ZK130692")
    tremol_operator_code = fields.Char(string="URN operator code", default="ODOO")
    tremol_vat_group = fields.Selection(
        selection=[
            ("А", "А"),
            ("Б", "Б"),
            ("В", "В"),
            ("Г", "Г"),
            ("Д", "Д"),
            ("Е", "Е"),
            ("Ж", "Ж"),
            ("З", "З"),
        ],
        string="Default VAT group",
        default="Б",
    )
    tremol_cash_payment_code = fields.Integer(string="Cash payment code", default=0)
    tremol_card_payment_code = fields.Integer(string="Card payment code", default=1)
    tremol_last_test_at = fields.Datetime(string="Last successful TREMOL test", readonly=True)

    @api.constrains(
        "tremol_com_port",
        "tremol_operator_password",
        "tremol_device_number",
        "tremol_operator_code",
    )
    def _check_tremol_settings(self):
        for company in self.filtered("tremol_enabled"):
            if not re.fullmatch(r"COM\d+", (company.tremol_com_port or "").upper()):
                raise ValidationError(_("The TREMOL port must look like COM4."))
            if not re.fullmatch(r"[A-Za-z0-9]{8}", company.tremol_device_number or ""):
                raise ValidationError(_("The fiscal device number must contain 8 letters/digits."))
            if not re.fullmatch(r"[A-Za-z0-9]{4}", company.tremol_operator_code or ""):
                raise ValidationError(_("The URN operator code must contain 4 letters/digits."))
            if len(company.tremol_operator_password or "") != 6:
                raise ValidationError(_("The TREMOL operator password must contain 6 symbols."))
