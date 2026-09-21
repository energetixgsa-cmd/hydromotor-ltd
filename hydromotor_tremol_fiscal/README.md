# Hydromotor TREMOL Fiscal — Odoo 19

Integration between Odoo customer invoices and a local TREMOL M23 through
ZFPLabServer 1.5.7.

## Safe workflow

1. Install and upgrade this module on the Odoo.sh development branch.
2. In **Settings → TREMOL**, verify the local address and device parameters.
3. Keep ZFPLabServer running on the Windows workstation connected to the device.
4. Open a posted and paid customer invoice and run **Test TREMOL connection**.
5. Only after a successful test use **Issue fiscal receipt** and explicitly
   confirm cash or bank-card payment.

The module never prints automatically when an invoice is posted. It records the
response on the invoice and prevents a normal second issue after success.

## Defaults for the photographed Hydromotor device

- ZFPLabServer: `http://127.0.0.1:4444/`
- Serial port: `COM4`
- Baud: `0` (automatic)
- Fiscal device number: `ZK130692`
- VAT group: `Б`

The operator password, payment codes, VAT group and URN operator code must be
confirmed against the programmed values in the fiscal device before the first
real receipt.

## Important browser requirement

Odoo.sh is remote, while ZFPLabServer is local. The TREMOL commands are therefore
sent from the user's browser to `127.0.0.1`. The browser must allow local-network
access and ZFPLabServer must allow the Odoo origin. If the connection test is
blocked, no fiscal command is sent and the invoice stores the returned error.

## Protocol

The receipt sequence is:

1. `Settings`
2. `ReadStatus`
3. `OpenReceipt`
4. `SellPLUwithSpecifiedVAT` for every invoice line
5. `Payment`
6. `CloseReceipt`

If an error occurs after opening a receipt, the module attempts `CancelReceipt`.

