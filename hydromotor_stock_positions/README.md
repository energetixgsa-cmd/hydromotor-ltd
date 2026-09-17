# Hydromotor stock positions

Optional Odoo 19.0 development candidate. Recovers the current product-template compute and sale-line related field from the backup; preserves their technical names.

The product forms use a new Stock positions tab rather than the obsolete experimental Studio location fields. Display is restricted to stock.group_stock_user to avoid stock-quant access errors and revealing inventory through an unrestricted view. Warehouse permission must be assigned deliberately.

This is not an import of all Studio customizations. The unused legacy Studio app, experimental location relations, optional-serial override, and positional quotation-report edits are retained in the separate review archive. No stock quantities are imported.
