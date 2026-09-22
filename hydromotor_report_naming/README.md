# Hydromotor Bilingual PDF Naming

Odoo 19 module for dynamic BG/EN PDF filenames based on the language of the partner selected on the document.

## Rule
- partner language starts with `bg` -> Bulgarian filename
- every other language -> English filename

Examples:
- `Оферта - S00045.pdf`
- `Offer - S00045.pdf`
- `Фактура - INV-2026-0045.pdf`
- `Invoice - INV-2026-0045.pdf`

## v19.0.1.0.2 fix
Odoo's `ir.actions.report.print_report_name` field is translatable. A Bulgarian UI translation of the report action could therefore override the dynamic filename expression, even while the PDF body correctly rendered in English for an English-language customer.

This version synchronizes the same dynamic Python expression into every active UI language during module install/upgrade. The expression itself then decides whether the filename is Bulgarian or English from `partner_id.lang`.

## Installation / upgrade
1. Replace the old `hydromotor_report_naming` folder with this version.
2. Push/merge it to the Odoo.sh branch.
3. In Odoo: Apps -> Update Apps List.
4. Open **Hydromotor Bilingual PDF Naming** and click **Upgrade**.
5. Test one partner with Language = Bulgarian and one with Language = English.
