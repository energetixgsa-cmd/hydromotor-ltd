from odoo import api, fields, models
from .article_utils import description_without_reference


class ProductProduct(models.Model):
    _inherit = "product.product"

    default_code = fields.Char(string="Article Number")

    def _hm_description_without_reference(self, description):
        self.ensure_one()
        return description_without_reference(description, self.default_code)

    @api.depends("name", "default_code", "product_tmpl_id")
    @api.depends_context("display_default_code", "seller_id", "company_id", "partner_id", "formatted_display_name", "lang")
    def _compute_display_name(self):
        # Let Odoo retain variant names, vendor names and access checks.
        clean = self.with_context(display_default_code=False)
        super(ProductProduct, clean)._compute_display_name()
        for record, clean_record in zip(self, clean):
            record.display_name = clean_record.display_name


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_code = fields.Char(string="Article Number")

    @api.depends("name", "default_code")
    @api.depends_context("formatted_display_name", "display_default_code", "lang")
    def _compute_display_name(self):
        clean = self.with_context(display_default_code=False)
        super(ProductTemplate, clean)._compute_display_name()
        for record, clean_record in zip(self, clean):
            record.display_name = clean_record.display_name


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )

    hm_description = fields.Text(
        string="Item Description", compute="_compute_hm_description",
        inverse="_inverse_hm_description", readonly=False,
    )

    @api.depends("name", "product_id.default_code", "display_type")
    def _compute_hm_description(self):
        for line in self:
            line.hm_description = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )

    def _inverse_hm_description(self):
        for line in self:
            current = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )
            if line.hm_description != current:
                line.name = line.hm_description


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )

    hm_description = fields.Text(
        string="Item Description", compute="_compute_hm_description",
        inverse="_inverse_hm_description", readonly=False,
    )

    @api.depends("name", "product_id.default_code", "display_type")
    def _compute_hm_description(self):
        for line in self:
            line.hm_description = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )

    def _inverse_hm_description(self):
        for line in self:
            current = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )
            if line.hm_description != current:
                line.name = line.hm_description


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )

    hm_description = fields.Text(
        string="Item Description", compute="_compute_hm_description",
        inverse="_inverse_hm_description", readonly=False,
    )

    @api.depends("name", "product_id.default_code", "display_type")
    def _compute_hm_description(self):
        for line in self:
            line.hm_description = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )

    def _inverse_hm_description(self):
        for line in self:
            current = (
                description_without_reference(line.name, line.product_id.default_code)
                if line.product_id and line.display_type in (False, "product")
                else line.name
            )
            if line.hm_description != current:
                line.name = line.hm_description

    def _get_aml_vals(self, hide_taxes):
        vals = super()._get_aml_vals(hide_taxes)
        vals["hm_article_number"] = self.hm_article_number or ""
        vals["name"] = self.hm_description
        return vals


class StockMove(models.Model):
    _inherit = "stock.move"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )

    def _get_aggregated_properties(self, move_line=False, move=False):
        vals = super()._get_aggregated_properties(move_line=move_line, move=move)
        # Odoo 19 carries the source move in aggregated delivery lines.
        vals["hm_article_number"] = vals["move"].product_id.default_code or ""
        vals["description"] = description_without_reference(vals["description"], vals["hm_article_number"])
        return vals


class StockQuant(models.Model):
    _inherit = "stock.quant"

    hm_article_number = fields.Char(
        string="Article Number", related="product_id.default_code", readonly=True,
    )
