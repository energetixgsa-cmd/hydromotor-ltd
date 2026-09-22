# -*- coding: utf-8 -*-
from odoo import models


def _is_bg(partner):
    """Return True when the document partner language is Bulgarian.

    Important: use the exact partner/contact selected on the document first.
    A child contact may be English even when its commercial company partner is Bulgarian.
    Only fall back to the commercial partner language when the selected partner has no language.
    """
    if not partner:
        return False

    lang = partner.lang
    if not lang and partner.commercial_partner_id:
        lang = partner.commercial_partner_id.lang

    return (lang or "").lower().startswith("bg")


def _safe_ref(value):
    """Keep filenames readable and avoid slashes from Odoo document sequences."""
    value = value or "Document"
    return str(value).replace("/", "-").replace("\\", "-")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _hm_sale_pdf_filename(self, force_proforma=False):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name)

        if force_proforma:
            label = "Проформа" if bg else "Proforma Invoice"
        elif self.state in ("draft", "sent"):
            label = "Оферта" if bg else "Offer"
        else:
            label = "Поръчка" if bg else "Sales Order"
        return f"{label} - {ref}"


class AccountMove(models.Model):
    _inherit = "account.move"

    def _hm_invoice_pdf_filename(self):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name if self.name and self.name != "/" else self.ref)

        labels = {
            "out_invoice": ("Фактура", "Invoice"),
            "out_refund": ("Кредитно известие", "Credit Note"),
            "in_invoice": ("Фактура доставчик", "Vendor Bill"),
            "in_refund": ("Кредитно известие доставчик", "Vendor Credit Note"),
            "out_receipt": ("Разписка", "Receipt"),
            "in_receipt": ("Разписка доставчик", "Vendor Receipt"),
            "entry": ("Счетоводна операция", "Journal Entry"),
        }
        bg_label, en_label = labels.get(self.move_type, ("Документ", "Document"))
        return f"{bg_label if bg else en_label} - {ref}"


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _hm_payment_pdf_filename(self):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name or self.ref)
        label = "Разписка за плащане" if bg else "Payment Receipt"
        return f"{label} - {ref}"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _hm_delivery_pdf_filename(self):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name)
        code = self.picking_type_id.code

        if code == "outgoing":
            label = "Стокова разписка" if bg else "Delivery Note"
        elif code == "incoming":
            label = "Приемна разписка" if bg else "Goods Receipt"
        elif code == "internal":
            label = "Вътрешен трансфер" if bg else "Internal Transfer"
        else:
            label = "Складов документ" if bg else "Stock Document"
        return f"{label} - {ref}"

    def _hm_picking_pdf_filename(self):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name)
        label = "Складова операция" if bg else "Picking Operations"
        return f"{label} - {ref}"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _hm_purchase_pdf_filename(self, force_rfq=False):
        self.ensure_one()
        bg = _is_bg(self.partner_id)
        ref = _safe_ref(self.name)

        if force_rfq or self.state in ("draft", "sent", "to approve"):
            label = "Запитване за оферта" if bg else "Request for Quotation"
        else:
            label = "Поръчка към доставчик" if bg else "Purchase Order"
        return f"{label} - {ref}"
