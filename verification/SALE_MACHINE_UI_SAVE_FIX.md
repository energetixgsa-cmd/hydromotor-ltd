# Testovo UI inheritance-save regression — 19.0.1.2.1

Source base: `82b55fa76d4932dbabf9462eb21bb5b2c153173f`.
Scope: Testovo only; no production deployment or sale/stock/accounting/mail transitions.

## Reproduction and correction

Captured actual header-only form-save args:

```json
[[49], {"x_hm_order_machine_id":45,"order_line":[[1,65,{"x_hm_parts_machine_id":45}]]}]
```

The browser omits the unchanged true inheritance flag. Previously line write interpreted the nested machine assignment as an explicit override. Order write now recognizes a matching header-onchange echo on already inherited lines belonging to the order and supplies the unchanged true flag before nested writes. Explicit false flags, different machines, existing explicit lines, direct line clears and line-only writes retain their previous override semantics. Input dictionaries are not mutated.

An explicit override to the same machine during a header change must include `x_hm_use_order_machine=False`; the payload otherwise is indistinguishable from the captured header-onchange echo. The existing UI exposes this checkbox.

The commercial-customer helper has its own label `Клиент за избор на машина`, rather than inheriting `Commercial Entity` and duplicating sale_subscription's field label.

## Executed local tests

Real Odoo 19 registry/PostgreSQL, not ORM doubles:
- `ui-inheritance-red.log`: one test failed on the missing unchanged true flag.
- `ui-inheritance-green.log`: exact request shape (only record IDs rebound), one test passed.
- `ui-label-red.log`: one test failed on `Commercial Entity` equality.
- `ui-fix-release.log`: 17 selected, zero failures/errors; optional local PDF test skipped (16 executed passes). Includes explicit override/False, subsequent cascade, header clear, SQL readback, actual Form, ACL and QWeb regression checks.
- Four pure-policy tests also pass.

Logs live under active-profile scratch `hm_odoo_runtime/`. Local PDF attempts without an independent serving asset endpoint timed out and are not counted as passes. Previous catalog baseline failure is unchanged and outside this fix.

## Deployment and rollback gate

Before push recheck Testovo source, unchanged main SHA, neutralization and recoverability. This patch adds/drops no fields or schema declarations. If behavior rollback is needed, revert only these behavior/label changes in a new compatibility commit with a forward version bump, retaining all 19.0.1.2.0 declarations and attribution values. Do not uninstall or downgrade the field-owning module. Take an exact DB+filestore snapshot of the current state first; full snapshot restoration loses later data and is not an attribution-preserving rollback.

Remote push, installed version, real UI saves and actual staging PDF acceptance are separate gates; this local record does not claim those passed. The external deployment receipt records their final status.
