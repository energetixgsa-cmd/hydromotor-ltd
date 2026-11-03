# Customer-machine attribution on sales (19.0.1.2.0)

## Behavior

- The order's **Машина за офертата** is an editable default directly below the
  customer (draft/sent only). Model and physical serial are shown separately.
- It is distinct from `sale.order.x_hm_machine_ids` (machines originally sold)
  and never writes `x_hm_machine.x_sale_order_id` or delivery/lot links.
- New product/service lines inherit the default. Uncheck **От машината на
  офертата** to select another customer machine or deliberately leave a line
  unassigned. Only inherited lines follow later header changes. Sections/notes
  have no machine. Existing kit-attributed lines remain explicit on upgrade;
  historical unassigned lines are not silently backfilled.
- API/import callers supplying `x_hm_parts_machine_id` explicitly (including
  `False`) override the default. Supplying `x_hm_use_order_machine=True`
  explicitly opts back into inheritance. Context defaults and batch creates
  obey the same contract.
- Both order and line assignments validate customer/commercial-contact family,
  company, active-service status and read access on the server. UI domains use
  `child_of` against the customer's commercial root, not a search on the
  nonstored `commercial_partner_id` of machine owners.
- Sales staff receive read-only machine access, still intersected with the
  service module's global allowed-company rule. No portal ACL is added.
- The dossier's **Оферти и продажби на части** page lists the actual linked
  `sale.order.line` records with ordered, net delivered and invoiced quantities.
  Offered, sold, partial/full delivery, net return and cancellation are separate
  states. **Delivery/sale is not proof of installation.** Standard sales record
  rules still control which lines each user can see.
- Kit/job provenance remains available as optional columns on the normal order
  lines. The old duplicate read-only `order_line` widget was removed because it
  overwrote the editable subview metadata/defaults.
- The actual sale report and Hydromotor's invoice-style proforma both print the
  header default and each line's own attribution. Explicitly unassigned lines
  do not fall back to the header. Machine labels/serials are escaped by QWeb.
  Actual invoices are excluded from the added proforma blocks.
- Reports read current dossier labels/serials, not an immutable historical
  snapshot. Reprinting after a dossier edit can therefore change that text.

## Local tests

Pure policy tests (no Odoo required):

```sh
python -m unittest discover -s tests -p test_sale_machine_policy.py -v
```

Use a disposable Odoo 19 / PostgreSQL database, the repository in `addons_path`,
mail/integrations disabled, and no cron workers:

```sh
odoo-bin -d DISPOSABLE_DB -u hydromotor_parts_kits \
  --test-enable --test-tags /hydromotor_parts_kits:TestSaleMachine \
  --stop-after-init --max-cron-threads=0 --workers=0
```

The module depends on `hydromotor_report_signatures` so the real custom
proforma is a required part of installation, not an optional untested template.
Tests create only synthetic draft quotations, lots, dossiers and users; they do
not call sale confirmation, stock validation, invoice posting or message-send
methods. Odoo's test runner also disables actual SMTP transmission. Test users
created by the new suite suppress signup/reset mail explicitly.

Set `HM_TEST_PDF=1` with patched-Qt wkhtmltopdf to force real PDF conversion
(`force_report_rendering=True`), verify `%PDF-`, parse both serial numbers and
optionally save documents with `HM_TEST_ARTIFACT_DIR`. `HM_TEST_REPORT_URL` can
point to an isolated HTTP asset server with the same report assets. Do not
reuse a blocked single-worker test HTTP server: a separate read-only asset
fixture DB avoids registry/DDL locks during test transactions. HTML tests run
without that opt-in and render the actual report actions, not QWeb mocks.

See `verification/SALE_MACHINE_TESTS.md` for observed results and limitations.

## Testovo-only deployment and rollback gates

Baseline remote Testovo:
`a0189f3fe4a6ce5b3d1ce9bc179ec4c80a8d4812`.
Main must remain:
`19b93ea2d6f96ed53b85e2c4d9afd345f7c3e51d`.

1. Verify the current Odoo.sh Testovo project/active build and exact Connect URL;
   an old build URL is not sufficient. Verify staging neutralization and a
   restorable database/filestore snapshot immediately before upgrade. Check
   whether `hydromotor_report_signatures` is already installed: this feature
   requires it, and installing it when absent also activates its existing
   invoice/report templates; review that impact before deployment.
2. Recheck both remote SHAs. Review the artifact, run authenticated
   `git push --dry-run origin HEAD:refs/heads/Testovo`, then fast-forward only
   the approved Testovo branch. Never force-push or push main.
3. Confirm the remote SHA, inspect Odoo.sh logs, explicitly upgrade
   `hydromotor_parts_kits` to `19.0.1.2.0`, and read back the installed version
   and new stored field from the current build. Run this suite on an isolated
   test DB and perform read-only UI/schema/report acceptance.
4. Never confirm a sale, validate a delivery or send a message as a deployment
   check without separate authorization.
5. On failure restore the verified pre-upgrade DB/filestore snapshot and revert
   only this feature commit on Testovo, or forward-fix after review. A Git
   revert alone is **not** database rollback: removing Python fields during a
   module upgrade can drop new columns. A manifest downgrade alone also does
   not guarantee that Odoo.sh reruns the required module update. Preserve both
   original revision and snapshot until acceptance completes.

Deployment must stop if the current staging identity, backup/restore access or
post-upgrade verification route cannot be established, even when Git transport
access succeeds. No production credential may be reused on staging.
