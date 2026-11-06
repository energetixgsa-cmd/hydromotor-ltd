# Hydromotor Sites and Concrete Plants — local Odoo 19 prototype

Version: **19.0.1.0.0**. Status: local tested code, **not deployed**. This is a Python addon, not a CSV/data-only import. A ZIP handoff does not install it in Testovo; importing source/installing the addon there requires separate authorization and an Odoo.sh/on-premise code deployment path.

## Business scope

- Existing `project.project` records represent **sites/projects**. This addon does not create a second competing site model.
- `hm.concrete.plant` represents a concrete batching **installation grouping machines at one site**, not an internal machine component. A site can have several plants.
- Existing `x_hm_machine` dossiers stay authoritative. A machine can have one current actual assignment, either directly to a site or to a plant within that site. It may also be unassigned.
- `x_partner_id` remains the machine's owner/customer. Assigning or moving it does not change ownership, serial, lot, sale order, or parts links. Site customer and machine owner need not be the same business.
- Sale order and line `hm_target_project_id` / `hm_target_plant_id` are **planned commercial destinations**. They do not mean equipment has been installed, even after sale confirmation or delivery. There is deliberately no automatic sale/stock-to-actual-assignment hook.
- Existing order `x_hm_machine_ids` (sold machines), order machine selector and line `x_hm_parts_machine_id` (parts target) remain distinct and unchanged. The addon neither redeclares nor repurposes them.
- No historic data is inferred/backfilled, no fake serial/stock lot is created, and no scheduler or outgoing integration is added.

## How to use after an approved installation

1. Create/select an existing Project and set its explicit company. Existing project visibility/ACLs still apply.
2. From **Sites and Plants → Concrete plants**, create a named plant linked to that project and company, if applicable. The project form also has a **Plants and machines** page.
3. Open an existing machine dossier and use **Assign / move existing machine**, or use **Actual machine assignments → New**. Select the actual site and optional concrete plant, and save. This is an explicit factual placement command, not a quotation default.
4. Saving closes the previous actual interval and opens the new interval atomically. Use **End actual assignment now** to leave it unassigned. Historic rows are immutable; correcting an assignment means ending/moving it and recording a new row. There is no backdating in this prototype.
5. On a quotation, select **Planned site / Project** and optional **Planned concrete plant** adjacent to the customer. New ordinary lines inherit them. Changing the header updates only inheriting lines. A line's explicit selection or clearing opts out; check **Use order planned destination** to opt back in. Selecting an identical value is not an explicit opt-out; clear that checkbox when a persistent override is intended.
6. For API changes, submit a consistent site/plant pair. Clearing a site with a populated plant requires clearing the plant too. The form onchange does this automatically.
7. Planned values remain editable commercial metadata; they are not immutable order-time snapshots and are not copied onto duplicated orders/lines. This addon does not add those labels to customer portal/PDF output.

## Data and implementation contract

- `hm.machine.assignment`: machine, actual project, optional plant, company, server-controlled UTC start/end, creator, note and `request_key`.
- Manual-model additions are XML `ir.model.fields` only: `x_hm_assignment_ids`, computed/nonstored `x_hm_site_id`, computed/nonstored `x_hm_plant_id`, and internal `x_hm_assignment_revision`. There is **no Python `_inherit = 'x_hm_machine'`**. Current location is derived from the open history row, not a second writable location authority.
- New stored many2one references use restrictive deletion. Machine-side location additions and quotation target fields are not copied. Existing machine ACLs and record rules are untouched.
- Sites must have an explicit company. Machine, site, plant and document company must agree, and the company must be allowed in the caller environment. Plant must belong to the selected site. New actual assignments require active sites/plants. Existing shared-company projects must be reviewed explicitly rather than silently assigned a company.
- Service users can create actual assignments and end them and can maintain plant records, subject to existing project/machine rights. Sales users get read-only access to the new plant/history models. No access is granted to public/portal users. Give relevant users the ordinary **Project User** role and project visibility as well as their existing sales/service roles; this addon does not bypass private-project rules or elevate with `sudo()`.
- Assignment creation uses the caller's machine write rights and an immediate ORM revision UPDATE/flush before reading history. PostgreSQL's partial unique index enforces one open row per machine. Under Odoo's REPEATABLE READ isolation, a losing concurrent worker must retry its **whole transaction with a fresh cursor/environment**; standard Odoo request handling retries serialization failures. External Python callers must implement that boundary too.
- A stable caller-supplied `request_key` (nonempty, up to 128 characters) makes a replay return the original interval without reopening it, even after a later move. Same key with changed site/plant/note is rejected. Default form creation generates a fresh UUID. API clients should retain their key across ambiguous retries; two independent new-form submissions are separate commands.
- Savepoints preserve atomicity even if a Python caller catches a rejected command. Multi-command results retain input order/cardinality, including replayed IDs.
- Seven composite database foreign keys and two narrowly owned unique indexes protect site/company integrity and plant reparenting, including races. Cross-model DDL is queued through Odoo 19's registry `post_init` queue so first installation does not depend on model initialization order. Referenced plant site/company and referenced project company cannot be changed; create another installation instead. SQL is limited to schema DDL and referential-existence checks, not business writes.
- Machine company immutability continues to be enforced by the existing Hydromotor automation. No replacement implementation or ACL override is introduced.

## Provenance

Read-only remote: `https://github.com/energetixgsa-cmd/hydromotor-ltd.git`, case-sensitive branch **Testovo**.

Inspected and rechecked source SHA: `8bb54923ebc3f328d8ae90322e44ccb2b1d6343a`.

Actual local Odoo 19 source: `5cd0bbc9cf6a554b5b91fbd0c0df3800f0744bc7`.

Only this new addon is delivered; existing tracked repository files are unchanged. The local test database was cloned from a pre-existing disposable synthetic test database, then the service, machine-sales and parts modules were upgraded from the inspected Testovo source. No remote Odoo database/API was accessed or written, and no Git push was made.

Official 19.0 references consulted:
- https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html
- https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html
- https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html

## Installation gate — future Testovo import, not performed here

Dependencies: `project`, `hydromotor_machine_sales`, `hydromotor_parts_kits`, plus their existing dependencies. Python code must be installed on the addon filesystem through the reviewed source deployment path. Do not use a generic data-import wizard or assume uploading this ZIP alone executes Python on Odoo.sh.

Before approved staging deployment:
1. Recheck Testovo SHA/source drift, review this addon and obtain scope approval for source import/install.
2. Create and verify a recoverable **staging database + filestore** backup, identify the serving staging database/build, and verify neutralized mail/external integrations. Do not use production credentials.
3. Extract only the `hydromotor_site_plant` folder into the staging addon path. Do not copy the local test databases, data directory, runtime or verification scripts into production.
4. Update the app list and install `hydromotor_site_plant` (or upgrade it for subsequent revisions). Equivalent isolated CLI test command:

   `odoo-bin -d <isolated_staging_test_db> -i hydromotor_site_plant --test-enable --test-tags=/hydromotor_site_plant --stop-after-init`

5. Verify installed version, cold registry load and effective machine/project/sale forms, then perform separately authorized staging fixture acceptance with actual intended service/sales users. Confirm project/company domains, line overrides/clearing, history/replay, existing parts/sold-machine relations and that quotation/confirmation does not install equipment.

**Known baseline bootstrap issue:** a completely blank database installing all current dependencies together failed before this addon loaded: `KeyError: Field x_hm_parts_machine_id referenced in related field definition sale.order.line.x_hm_parts_machine_serial does not exist.` This is the existing parts module's Python-related/XML-field initialization order. Existing dependency source was not modified to mask it. Installation of this addon on already-installed dependencies and subsequent upgrades were executed successfully. A full greenfield bootstrap of the whole repository is **not** claimed.

## Rollback

Preferred lossless rollback: stop staging writes, restore the pre-install staging database **and filestore**, restore the reviewed previous source and restart/verify its registry. Never just remove the Python addon directory while the module is installed.

Uninstalling only this addon is a destructive alternative: it removes plants, assignment history, planned destinations and addon-owned fields/views. Its uninstall hook removes owned composite FKs and the owned core-table index, while preserving machine/project/sale records and original machine-sales field definitions. Export any history/planned data first if it matters. An uninstall does **not** recreate that data on reinstall. The destructive route was exercised only on a separate local disposable clone; full database+filestore restore and Odoo.sh rollback were not exercised.

## Exact verification status

Executed against real local Odoo 19 + PostgreSQL 17, not ORM doubles:
- 12 addon TransactionCase methods: persisted current/history roundtrip, owner preservation, movement/closure/replay, immutable history, site/company checks, protected original machine-company guard, restricted roles, hidden foreign-company project denial, planned destinations/line overrides/clearing/copy, web_save echo, real local sale confirmation without installation, effective views/Odoo Form creation, schema constraints, failed-command atomicity and batch replay cardinality.
- Final selected dependency regression run: **25 tests, 0 failures, 0 errors** (12 new + 7 existing service + 4 existing machine registry + 2 existing parts-machine selection tests). This is a selected suite, not every repository test. Baseline uniqueness-negative tests intentionally log a SQL duplicate-key error; that is expected test evidence, not a failed suite. Dependency upgrade logs also contain pre-existing docutils formatting warnings from recovered metadata.
- First installation/reinstallation on already-installed dependencies: **12 tests, 0 failures, 0 errors**. A first-install-only cross-model DDL ordering defect was reproduced and fixed; failed evidence is retained as well as its green rerun.
- Two real concurrent worker cursors on different destinations: one full-transaction serialization retry, preserved owner and nonoverlapping history. A second concurrent round with the same request key returned the same assignment ID to both workers, without a duplicate. Final read-back: 3 intervals, 1 open interval.
- Destructive uninstall on another disposable clone preserved existing machine/project/sale record counts and original machine-sales field definitions and removed addon-owned constraints/index; reinstall passed.
- Each feature slice has retained RED and GREEN logs. The assertion helper in one atomicity test was tightened because Odoo's helper inserts an implicit savepoint; final RED really reproduced the missing atomic boundary before the fix.

Not executed / not claimed:
- Any Testovo installation, staging browser click-through, live restricted-user or customer portal/PDF acceptance.
- Full repository test suite, every ACL combination, Enterprise-specific behavior, production scale/performance, backup restore, upgrade from another version of this new addon, backdated/correction workflows, automatic installation/delivery mapping or customer-facing PDF/portal destination output.
- Full clean bootstrap of all current repository dependencies (blocked as above).

The handoff contains readable source and tests. `evidence/test-results.json`, `concurrency.json`, `lifecycle.json`, exact runner scripts and full RED/GREEN logs accompany the separate evidence archive. No credentials, environment files, business backup or runtime binaries are packaged.
