# Hydromotor Report Signatures - Odoo 19

This addon is intentionally separate from `hydromotor_report_naming`, so PDF file naming and existing import/data logic stay untouched.

## Invoice
For outgoing customer invoices (`out_invoice`) it adds:
- `Съставил / Prepared by` - automatic from the invoice responsible user (`invoice_user_id`), with safe fallback to the creator (`create_uid`).
- `Издал / Предал / Issued / Handed over by` - blank line for handwriting.
- `Приел / Accepted by` - blank line for handwriting.
- A signature line under all three sections.

The automatic preparer name is bilingual when the user's two document-name fields are filled. Otherwise it falls back safely to the normal Odoo user name.

For the existing Hydromotor user whose name contains `Georgi Aenski`, installation seeds:
- BG: `Георги Аенски`
- EN: `Georgi Aenski`

This does not change the Odoo login or the normal user name.

## Quotation
For quotations in `draft` or `sent` state it adds:
- `Предал / Handed over by` - blank line.
- `Приел / Accepted by` - blank line.
- Signature line under both sections.

## User setup for other users
Settings -> Users -> open the user -> Preferences -> `Печат на документи / Document Printing`:
- `Име за документи (BG)`
- `Document name (EN)`

After that every outgoing invoice uses the bilingual preparer name automatically.

## Install
1. Put the `hydromotor_report_signatures` folder in the Odoo.sh custom addons repository root.
2. Commit/push to the `hydromotor` branch.
3. Wait for Odoo.sh build.
4. Apps -> Update Apps List.
5. Install `Hydromotor Report Signatures`.

The addon does not modify existing imports, products, customers, invoices, quotations, or PDF naming logic. It only adds two user configuration fields and report layout inheritance.
