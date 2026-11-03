# Sale-machine verification record

Observed locally on 2026-11-02. This is **not** a staging-installation claim.

## Revisions / environment

- Feature worktree: `hm_sale_machine_current`, branch `hm-sale-machine-current`.
- Started from current remote Testovo
  `a0189f3fe4a6ce5b3d1ce9bc179ec4c80a8d4812`, not main or the flawed earlier
  local `887927e` implementation.
- Remote main remained `19b93ea2d6f96ed53b85e2c4d9afd345f7c3e51d`.
- Real Odoo 19 community source
  `5cd0bbc9cf6a554b5b91fbd0c0df3800f0744bc7`, isolated Python 3.12,
  PostgreSQL 17.7 on loopback port 55439, patched-Qt wkhtmltopdf 0.12.6.
- Disposable DB `hm_machine_tdd`; unchanged baseline worktree at the exact
  Testovo SHA and separate DB `hm_machine_baseline`.
- Baseline/current installed-module name sets were checked equal after installing
  the existing report-signatures module in the baseline fixture too.
- Local SQL readback confirms parts module `19.0.1.2.0`, a real integer
  `sale_order.x_hm_order_machine_id` column, Python/base stored order/origin
  fields, and XML/manual existing line-machine/new dossier-history fields.
  Baseline is `19.0.1.1.1` and has only the original per-line attribution field.

Scratch root used below:
`C:/Users/admin/AppData/Local/hermes/profiles/odoo-integration/cache/scratch`.
The isolated runner is `run_hm_odoo_test.py`; logs are in `hm_odoo_runtime/`.

## Observed test outputs

| Run | Exact test summary / outcome |
| --- | --- |
| Pure policy unittest | `Ran 4 tests` / `OK` |
| `machine-acceptance-final.log` | `0 failed, 0 error(s) of 13 tests`; exit 0, real PDFs enabled |
| `machine-full-final.log` | `1 failed, 0 error(s) of 34 tests`; exit 1, optional PDF test skipped in this run |
| `machine-regression-green.log` | `0 failed, 0 error(s) of 32 tests`; exit 0; excludes the baseline catalog failure and the separately exercised PDF test |
| `machine-catalog-baseline-matched-final.log` | unchanged Testovo: `1 failed, 0 error(s) of 1 tests`; exit 1 |

The Odoo `tests.stats` line also counts setup/teardown methods and has a larger
number; the table uses actual `odoo.tests.result` test totals, not that number.
These are overlapping runs, not additive test counts.

TDD red-to-green logs also include `machine-red`, `machine-override-red`,
`machine-validation-red`, `machine-form-red`, `machine-history-red`,
`machine-report-red`, `machine-acl-red`, `machine-context-red`, and
`machine-ui-context-red`. The final context regression failed first on an
explicit `default_x_hm_parts_machine_id=False` being misinterpreted as an
inheritance request; it passed after `default_get` honored explicit context.

Acceptance covers actual persisted ORM/SQL readback, copy semantics, nested and
batch lines, context defaults, reparenting, explicit overrides and explicit
False, note lines, header propagation, customer/contact/company/retired
validation, sales-only ACLs and cross-company denial, real Form interactions,
selector position and evaluated domain, dossier line history, original machine
sale links remaining independent, actual quotation/custom proforma QWeb,
Bulgarian labels, escaping and mixed/unassigned machine lines.
Commercial/delivery statuses use unsaved synthetic quantities: there was no
sale confirmation, stock validation or real business transition.

### Existing failing regression

`TestCatalogProductSearch.test_product_edits_and_ambiguity_are_dynamic`, line
114, fails at:

```python
self.assertIn(self.implicit, self._assert_computed_search('=', False))
```

It fails on both the implementation DB and the unchanged current Testovo
baseline with the same installed modules. It is not hidden or fixed by changing
unrelated catalog behavior. Therefore the full parts suite is **not all green**.
Existing manifest-description docutils indentation warnings also appear during
module upgrades; they do not produce failed installation/test results.

## Actual PDF artifacts

Both actual report actions ran through `_render_qweb_pdf` with
`force_report_rendering=True`. Tests checked `%PDF-`, parsed model names and
serials, verified header/inherited/override occurrence counts, and confirmed
that the unassigned line did not inherit the header in print.

- `hm_odoo_runtime/artifacts/machine-sale.pdf`: 24,496 bytes, one page,
  SHA-256 `dedd0fd79748eff333fcb56c40e3cf64f11319e3a6dd7de69efb41adf647def9`.
- `hm_odoo_runtime/artifacts/machine-proforma.pdf`: 24,521 bytes, one page,
  SHA-256 `26b0874f6e556fe1664895e2953f34544b620275026473f0a1ec5c242bc4b922`.
- Matching `.png` page renders were visually reviewed: readable default/model/
  serial, correctly different override, untagged unassigned line, no observed
  overlap or clipping in these synthetic one-page documents.

These are local synthetic quotations/proformas, not customer documents. Fonts
and CSS were fetched by real wkhtmltopdf from a loopback fixture asset server;
there were no mocked report methods. Early attempts without a serving HTTP
asset endpoint and with same-DB registry/DDL locks were stopped, not counted as
successful PDF verification. The final isolated asset fixture resolved them.

## Deployment checkpoint / unresolved blockers

Git transport write access was checked with an authenticated Testovo dry run.
A new-commit dry run and preserved Git rollback bundle are recorded in the
completion handoff; neither means the Odoo database was upgraded.

The current Odoo.sh project URL redirects to GitHub OAuth login, and the browser
vault reports no saved login. Consequently the current active Testovo build,
neutralization and database/filestore backup/restore access could not be
verified. The historical build-specific Connect URL is not accepted as current
proof. No production credential was used on staging.

**No push/deployment was performed.** Do not bypass this gate: obtain the
current signed-in Testovo Odoo.sh session and a verified restorable pre-upgrade
snapshot, resolve or explicitly accept the known baseline regression, then
follow `hydromotor_parts_kits/SALE_MACHINE_ATTRIBUTION.md`. Git-only rollback is
not database rollback. The exact Odoo.sh server revision/enterprise addons were
not available for local equivalence verification.
