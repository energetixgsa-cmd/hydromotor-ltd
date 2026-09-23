# Hydromotor Report Signatures — Odoo 19

Version 19.0.1.2.7.

## Invoice-data field mapping

The partner form contains a dedicated **Данни за фактура / Invoice data** block.

- **Име / Name** -> standard `res.partner.name`
- **Адрес / Address** -> standard `street`, `street2`, `zip`, `city`, `country_id`
- **ЕИК / БУЛСТАТ** -> standard `company_registry`
- **ДДС №** -> standard `vat`
- **МОЛ / Представляващ** -> `hm_mol_bg`
- **Официално име на английски** -> `hm_name_en`
- **Официален адрес на английски** -> `hm_address_en`
- **МОЛ / Представляващ на английски** -> `hm_mol_en`
- **Език на документите** -> standard `lang`

For Bulgarian VAT numbers, the report can use the digits after `BG` as an EIK fallback when `company_registry` is still empty. MOL/legal representative is optional in the report and is not printed as a blank line when no value has been entered.

# Hydromotor Report Signatures — Odoo 19

Version 19.0.1.2.0.

## What this version changes

- Customer invoices use a dedicated Bulgarian-compliance layout for Hydromotor.
- Bulgarian customers receive Bulgarian labels; foreign customers receive English labels according to partner language/country.
- Supplier and customer blocks include legal name, address, Company ID/EIK, VAT number and legal representative/MOL.
- Invoice lines show Item No. separately from Description, Quantity, Unit, Unit Price excl. VAT, Discount, VAT and Tax Base.
- Invoice header includes Issue Date, Date of Supply, Due Date, Currency and Reference.
- Payment terms, IBAN/BIC and fiscal-position/legal VAT notes are printed when available.
- Invoice signatures are single-language according to the customer.
- Quotation and Sales Order signatures are also single-language according to the customer.
- Pro-forma uses the exact same invoice-style template as the customer invoice; only the document title changes to Pro-forma Invoice.

## New master-data fields

Contacts/companies now have:
- `Legal name (EN)`
- `Legal address (EN)`
- `МОЛ / Представляващ`
- `Legal representative (EN)`

Fill the English fields only where an English/Latin presentation is required.

## Upgrade

Replace the existing `hydromotor_report_signatures` addon folder, rebuild Odoo.sh, then upgrade the module from Apps.


## v1.2.2 UI clarification
- Dedicated full-width Invoice Data section on partner/company forms.
- Explicit labels for EIK/BULSTAT, VAT No., MOL/legal representative and document language.
- Separate foreign-document fields for EN legal name, address and representative.
- Original VAT/language placements hidden to avoid duplicate entry points.


## Version 19.0.1.2.5

- Added an explicit **Банкова сметка за документа** field on quotation/sales order.
- Pro-forma prints the selected sales-order bank account instead of always using the first company account.
- Invoices created from the sales order inherit the selected bank account into `partner_bank_id`.
- Document language is country-driven: Bulgarian customer = Bulgarian; foreign customer = English.
- VAT label follows the same rule: **ДДС №** for Bulgarian customers, **VAT No.** for foreign customers.


## 19.0.1.2.5
- Reduced the excessive blank space between the last company-address line and the VAT/Tax ID line in the report header.
- The address line spacing itself is unchanged.


## Version 19.0.1.2.5

- Bulgarian counterparties print **ЕИК**.
- Foreign counterparties print **Company ID / UIC**.
- Customer invoices are rendered as two copies in one PDF: **ОРИГИНАЛ / ORIGINAL** followed by **КОПИЕ / COPY**.
- Pro-forma invoices remain a single invoice-style document and are not duplicated as original/copy.


## Version 19.0.1.2.7

- Invoice/pro-forma number is rendered explicitly and prominently above all document fields as `ФАКТУРА № ...` / `INVOICE № ...`.
- ORIGINAL/COPY marker stays on the same top row as the document number.
- Company VAT line in the external report header is pulled directly under the last address/country line; Bootstrap/HTML paragraph bottom margins are reset for the company address block.


## 19.0.1.2.7

- Fixes the Hydromotor header gap between the last address line (e.g. Bulgaria) and VAT/Tax ID.
- The spacing rule now lives inside `web.external_layout_standard`'s actual header so it survives Odoo PDF header extraction.
- Pulls only the VAT row upward; address line spacing is unchanged.
