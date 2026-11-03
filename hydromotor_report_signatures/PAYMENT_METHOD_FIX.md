# Payment-method regression fix (local candidate, not deployed)

Version: `hydromotor_report_signatures 19.0.1.2.10`.
Base: production Git branch `main`, commit `322e6f967e5db256b651a85efb64d66aa6878270`.

## Verified diagnosis

- The live read-only metadata identifies Odoo **19.0+e**, installed report module **19.0.1.2.9**, and the actual method field **`preferred_payment_method_line_id`** on both `sale.order` and `account.move`. Its relation is `account.payment.method.line`; it is not payment terms, a recipient bank, or a payment registration.
- Official Odoo 19 `sale.order._prepare_invoice()` already transfers that field. The custom override previously transferred the selected `hm_partner_bank_id` to invoice `partner_bank_id`, without discarding the standard method. Real local ORM tests pass for an individual cash/bank/unset choice on the unchanged implementation. No redundant transfer override was added.
- The custom Bulgarian-company invoice body omits the method while showing payment terms and IBAN. The new report regression failed with **0 method rows instead of 2** (original + copy), then passed after adding the conditional row.
- Standard sale invoice grouping omits method and recipient bank. Real grouped-creation regression reproduced **one invoice instead of two** for different methods, different selected banks, and unset versus selected method. Such grouping silently keeps one prepared value. The candidate adds these choices to grouping keys. This is a real local defect, **not proof that grouping caused the sampled historical live blanks**.
- A deliberately bounded read-only source-linked sample found sale orders 3/7 with methods 11/12 and linked invoices 1/2/3 with unset methods. Their historical field-change sequence and deployed core/Enterprise behavior cannot be reconstructed from these reads. No matching code server action referencing this field was found. **The exact historical loss mechanism remains unproven.**

## Scope and semantics

- Print the **invoice's own current stored method name**, not its originating order's later choice. Hide the row when unset; escape its contents. BG customers receive `Начин на плащане:`, foreign customers `Payment Method:`. Method names themselves are existing configured names, not invented translations; `account.payment.method.line.name` is not translatable in the inspected core.
- The same invoice-style body serves pro-forma. No separate portal ACL/controller changes are needed: invoice Preview's standard iframe renders the same invoice report.
- Compatible orders can still merge. Different intended methods or recipient-bank choices produce separate new draft invoices. A cleared order bank is passed explicitly as False rather than silently replaced during creation. The pre-existing report's company-bank fallback is otherwise unchanged.
- No new fields, schema migration, history backfill, stored computed synchronization, payment registration, posting, receipt issuance, stock action, mail sending, scheduled job, or remote business write.
- Existing invoice overrides remain authoritative. Historical invoices with no method continue to have no method; they are not inferred from orders or actual payments.
- This fixes missing **payment-method content** in PDF/Preview. It is not evidence of, or a change to, an absent Preview button, broken PDF action, or an already generated immutable legal PDF attachment.

## Regression tests

`tests/test_payment_method.py` uses real Odoo ORM/PostgreSQL and HTTP, no business-object doubles:

1. Cash/bank/unset transfer to a draft; explicit unset wins over partner default; terms stay distinct; no registered payment; explicit invoice override survives later source edit.
2. Different methods/banks do not merge, compatible choices still merge.
3. Original/copy HTML print the actual escaped method; unset hides the row.
4. Cleared versus selected bank stays separate.
5. Authorized public/token portal page -> actual HTML iframe in BG/EN; Download link exists; invalid token does not disclose the method.
6. Actual wkhtmltopdf `%PDF-` output for cash/bank/unset × BG/EN, both copies, no false paid claim.

Example (use an **isolated disposable** Odoo 19 DB, never production):

```bash
odoo-bin --addons-path=/path/to/odoo/addons,/path/to/repo \
  -d DISPOSABLE_DB -u hydromotor_report_signatures \
  --test-enable --test-tags=/hydromotor_report_signatures:TestPaymentMethod \
  --max-cron-threads=0 --workers=0 --stop-after-init
```

For PDF acceptance set `HM_TEST_PDF=1`, expose local HTTP assets with patched-Qt wkhtmltopdf available, and optionally set `HM_PAYMENT_ARTIFACTS` to save PDFs/text. `HM_TEST_REPORT_URL` can point to a separate local asset server. The local tested Odoo core revision was `5cd0bbc9cf6a554b5b91fbd0c0df3800f0744bc7` (Community core); target Enterprise add-ons still require staging verification.

## Proposed approval boundary (not authorization)

Approve only this module/version/artifact on **Testovo**, currently `acc2463a3e7723df4478fdda578e82365c2b8046`; the report module is identical between that branch and current main. Preserve Testovo's unrelated machine/catalog changes; do not merge them into main. Verify active staging host, separate staging key, neutralization, integrations and recoverable backup first.

Then upgrade **only `hydromotor_report_signatures`** and run the automated disposable regression suite on staging/test DB. Any manual business acceptance must be separately scoped to newly named sandbox fixtures, limited to draft creation; no existing quotations/invoices modified, no confirmations, posting, payments, fiscal receipt or mail. Validate cash/bank/unset, grouping and overrides, backend field, BG/EN PDF and authorized Preview, including actual Enterprise overrides. Production promotion needs separate approval after that result.

Rollback: revert only this candidate module's changes to the pre-candidate Testovo revision and explicitly upgrade the module to restore prior QWeb. If sandbox invoices were created, code rollback does not merge/delete them; retain or remove only with scoped fixture approval. Production main remains unchanged. No rollback is permission for financial history rewrites.
