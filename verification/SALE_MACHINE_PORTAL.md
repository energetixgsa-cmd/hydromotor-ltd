# Sale customer portal machine display — 19.0.1.2.2

Scope: Testovo only. No promotion to main is authorized.

## Implementation and security boundary

`views/sale_machine_portal.xml` inherits the official Odoo 19
`sale.sale_order_portal_content`. Source inspected at Odoo Community commit
`5cd0bbc9cf6a554b5b91fbd0c0df3800f0744bc7`:
https://github.com/odoo/odoo/blob/5cd0bbc9cf6a554b5b91fbd0c0df3800f0744bc7/addons/sale/views/sale_portal_templates.xml

Verified anchors: `div#informations`, `td[name=td_product_name]`, and
`td[name=td_combo_name]`. Separate XPaths are intentional: Odoo inheritance
applies the first matching node, not every node in a union expression.

The default header and each actual line relation call the existing escaped
model/name-and-serial identity template. There is no header fallback on cleared
lines. Empty relations hide the complete block. No dossier hyperlink, notes,
service history, registration, engine number or other dossier fields are added.
Like the existing PDFs, these are current labels, not historical snapshots.

No new controller, public method, sudo call, machine ACL or record rule is
introduced. The standard `sale.controllers.portal.CustomerPortal.portal_order_page`
first calls `_document_check_access('sale.order', order_id, access_token)` and only
then supplies the authorized elevated order to QWeb. That standard authorization
is the boundary; a valid token deliberately permits this order's own identity
labels, not direct machine-model access. Missing/invalid/cross-order tokens stay
rejected. See official sale controller and portal controller at the same commit.

## Executable verification

Run in a disposable real Odoo 19/PostgreSQL database with the existing modules
installed; never on a live business database:

```sh
odoo-bin -d DISPOSABLE_DB -u hydromotor_parts_kits --test-enable \
  --test-tags /hydromotor_parts_kits:TestSaleMachinePortal \
  --stop-after-init --max-cron-threads=0 --workers=0
```

The HTTP suite covers internal Preview, authenticated customer portal, public
valid token, missing/invalid/cross-order token rejection, direct machine ACL
denial, unrelated dossier notes excluded, escaped labels, inherited/override/
explicitly-cleared lines, no machine, and a line override without a header.
Requests use `Odoo-Link-Preview: True` so public draft inspection does not post
Odoo's standard quotation-viewed note. No confirmation, delivery, invoice or
outbound mail action is called.

The full local owning-module suite has a pre-existing failure in
`TestCatalogProductSearch.test_product_edits_and_ambiguity_are_dynamic`; it is
reproduced with unchanged Testovo source. Do not broaden this portal patch to
change that unrelated catalog behavior. Real PDF tests are opt-in and are not
claimed by this portal change.

## Deployment and rollback

Start from Testovo `f3687b473d72b49e14399243bc4de949f2a4e461` and verify
main remains `3019936f6ba36270e5df59a1d91c13b7473f0a8e`. Require a fresh exact
Testovo database + filestore archive, CRC/hash/dump verification, and matching
Restore target before push. Read back remote SHA, module version, build/logs,
and the actual S00049 customer Preview after deployment; a green build alone
is not acceptance.

This patch adds no stored fields or schema changes. Behavior rollback removes
only the portal view/test import and advances to an explicitly higher patch
version for upgrade. Keep all pre-existing 19.0.1.2.1 Python/XML field declarations
and data. Never uninstall, remove attribution columns or blindly revert the
older machine feature. A full snapshot restore is disaster recovery to the
snapshot time, not a way to preserve later business data. Take a post-upgrade
snapshot before a real rollback. Rehearse source-revert + module-upgrade in the
disposable database before using it on Testovo.
