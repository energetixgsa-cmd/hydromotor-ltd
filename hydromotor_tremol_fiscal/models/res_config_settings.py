from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tremol_enabled = fields.Boolean(related="company_id.tremol_enabled", readonly=False)
    tremol_server_url = fields.Char(related="company_id.tremol_server_url", readonly=False)
    tremol_com_port = fields.Char(related="company_id.tremol_com_port", readonly=False)
    tremol_baud_rate = fields.Integer(related="company_id.tremol_baud_rate", readonly=False)
    tremol_keep_port_open = fields.Boolean(
        related="company_id.tremol_keep_port_open", readonly=False
    )
    tremol_operator_number = fields.Integer(
        related="company_id.tremol_operator_number", readonly=False
    )
    tremol_operator_password = fields.Char(
        related="company_id.tremol_operator_password", readonly=False
    )
    tremol_device_number = fields.Char(
        related="company_id.tremol_device_number", readonly=False
    )
    tremol_operator_code = fields.Char(
        related="company_id.tremol_operator_code", readonly=False
    )
    tremol_vat_group = fields.Selection(
        related="company_id.tremol_vat_group", readonly=False
    )
    tremol_cash_payment_code = fields.Integer(
        related="company_id.tremol_cash_payment_code", readonly=False
    )
    tremol_card_payment_code = fields.Integer(
        related="company_id.tremol_card_payment_code", readonly=False
    )
    tremol_last_test_at = fields.Datetime(related="company_id.tremol_last_test_at", readonly=True)
