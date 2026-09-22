# Hydromotor Bilingual PDF Naming - Odoo 19

The module changes only the downloaded/generated PDF filename. It does not change document sequences or document content.

## Language rule
- Partner language starts with `bg` -> Bulgarian filename
- Any other language or empty language -> English filename

The commercial partner language is used.

## Covered documents
- Sales quotation -> `Оферта - S00001.pdf` / `Offer - S00001.pdf`
- Sales order -> `Поръчка - S00001.pdf` / `Sales Order - S00001.pdf`
- Proforma -> `Проформа - S00001.pdf` / `Proforma Invoice - S00001.pdf`
- Customer invoice -> `Фактура - INV-2026-0001.pdf` / `Invoice - INV-2026-0001.pdf`
- Customer credit note -> `Кредитно известие - ...` / `Credit Note - ...`
- Vendor bill / vendor credit note
- Payment receipt
- Delivery note / goods receipt / internal transfer
- Picking operations
- Purchase RFQ / purchase order

## Install on Odoo.sh
1. Copy folder `hydromotor_report_naming` into the custom addons repository.
2. Commit and push to the target branch.
3. Wait for the Odoo.sh build.
4. Apps -> Update Apps List.
5. Search for `Hydromotor Bilingual PDF Naming` and install it.
6. Test one Bulgarian partner (`Language = Bulgarian`) and one foreign partner (`Language = English`, German, etc.).

## Important
This module targets Odoo 19.0 report external IDs verified against Odoo 19.0 source.
