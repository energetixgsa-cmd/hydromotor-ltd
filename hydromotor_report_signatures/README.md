# Hydromotor Report Signatures — Odoo 19

Version 19.0.1.1.0.

## Documents covered

- Customer invoice (`account.move`, outgoing invoice):
  - automatic **Съставил / Prepared by** with BG/EN document name;
  - blank **Издал / Предал / Issued / Handed over by**;
  - blank **Приел / Accepted by**;
  - signature line under all three.
- Quotation (`sale.order`, draft/sent):
  - blank **Предал / Handed over by**;
  - blank **Приел / Accepted by**;
  - signature line under both.
- Sales Order (`sale.order`, confirmed): same signature block as quotation.
- Pro-forma invoice (`sale.order` pro-forma): invoice-style structure plus the 3-column invoice signature block.

## Why the implementation changed

Earlier versions inherited only the standard invoice and sale-order report bodies. Studio/custom reports can replace those bodies, so the signature block could disappear. Version 19.0.1.1.0 inserts the block centrally through `web.external_layout`, which is the common external printing layout used by standard and Studio-derived reports.

## Upgrade

Replace the existing `hydromotor_report_signatures` addon folder, rebuild Odoo.sh, then upgrade the installed module from Apps.
