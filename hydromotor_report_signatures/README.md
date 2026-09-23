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
