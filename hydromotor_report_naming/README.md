# Hydromotor Bilingual PDF Naming

Odoo 19 module for dynamic Bulgarian/English PDF filenames and bilingual employee/user names in customer documents.

## Language rule
- Partner language starts with `bg` -> Bulgarian document name
- Any other language -> English document name

## PDF filenames
Examples:
- `Оферта - S00045.pdf` / `Offer - S00045.pdf`
- `Фактура - INV-2026-0045.pdf` / `Invoice - INV-2026-0045.pdf`

## Bilingual user / "Prepared by" names (v19.0.1.0.3)
Each Odoo user gets two optional fields:
- **Document Name (Bulgarian)** - e.g. `Иван Иванов`
- **Document Name (English)** - e.g. `Ivan Ivanov`

The normal Odoo user name remains unchanged. Reports use the partner language and fall back to the normal user name if the corresponding document-name field is empty.

The module enables this report-name context for Sales, Customer Invoices/Credit Notes, Purchase Orders/RFQs and Delivery Notes. It is designed to work automatically when the report prints a user as a many2one field (`t-field="...user_id"`).

If a custom/Studio invoice template explicitly prints `.name` (for example `o.invoice_user_id.name`) instead of the user field, that exact custom template must be adjusted to call `_hm_report_name(...)`; the standard Odoo 19 invoice template does not itself contain a "Prepared by" user line.

## Upgrade
1. Replace the old `hydromotor_report_naming` folder.
2. Push/merge to the Odoo.sh branch.
3. Apps -> Update Apps List.
4. Upgrade **Hydromotor Bilingual PDF Naming**.
5. Open your user -> Preferences -> **Document Names** and fill both fields.
6. Test one Bulgarian partner and one English/foreign partner.
