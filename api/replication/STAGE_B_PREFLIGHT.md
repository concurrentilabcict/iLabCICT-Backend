# Stage B preflight — 2026-11-02

Historical checkpoint. The final audit and owner-executed procedure are in
[FINAL_RESULTS.md](FINAL_RESULTS.md) and [DEPLOYMENT.md](DEPLOYMENT.md). A guarded, dry-run-first
scheduler repair command was subsequently prepared and tested locally; no production repair ran.

## Current deployment status

B1 read-only inspection and B2 source review/integration tests are complete. Activation is
blocked by an unequal scheduler baseline and unconfirmed production maintenance prerequisites.
B3 migrations, B4 trigger activation, B5 production processing and B6 scheduling have not run.
No automatic failover or routing change exists. Singapore remains the configured default.

The user requested strictly read-only production checks. No supplied login credentials were used;
the login endpoint writes an existing business audit entry, so authenticated business checks were
not performed. No production record, sequence, schema, trigger, role or schedule was changed.
Isolated integration tests used disposable local PostgreSQL databases only.

Django 6.0.4 is running locally at `http://127.0.0.1:8000/` with normal project settings,
replication disabled, and no system-check issues. It uses the configured Neon databases, not
the disposable integration-test databases. GET `/api/ping/` returned 200; unauthenticated GET
`/api/replication/status/` returned 401. The normal startup warning about the two unapplied
replication migrations is expected; no migration was automatically applied.

The configured Render service returned 503. The user confirmed it was intentionally paused;
this is not evidence of an application regression. Keep it paused through an approved cutover.
Live Render build/release settings, deployed revision and QStash account configuration remain
unverified: no dedicated service connector was available, and Chrome computer-use access was
not approved. No credentials were obtained from unrelated sources.

## Verified production facts

| Check | Singapore (`default`) | Sydney (`recovery`) |
| --- | --- | --- |
| Configured AWS region | ap-southeast-1 | ap-southeast-2 |
| Endpoint fingerprint (not a hostname or credential) | 043e0a9f1a41e67b | b621ad3ea47dfdf3 |
| Connection and database-name match | Verified | Verified |
| PostgreSQL version | 17.11 | 18.6 |
| Inspection transactions | READ ONLY | READ ONLY |
| Approved application/support tables | All 22 present | All 22 present |
| Unexpected public tables | None | None |
| Applied replication migration | 0001_initial | 0001_initial |
| Applied migration inventories | Equal | Equal |
| Non-internal triggers | None | None |
| Outbox pending / failed / applied | 0 / 0 / 0 | 0 / 0 / 0 |
| Legacy outbox events / receipts | 0 / 0 | 0 / 0 |
| Outbox sequence cache / increment / cycle | 1 / 1 / false | 1 / 1 / false |
| Configured role has business DML privileges | Yes | Yes |
| Existing connection timeout option | Not configured | Not configured |

Both are independent writable PostgreSQL projects, not a physical primary/standby pair. The
recovery connection needs DML privileges for replay, so its role being writable is expected;
ordinary application/admin/external writers must still be fenced from Sydney. An observed zero
other active transactions is not proof of an ongoing write fence.

All primary keys, FKs, uniqueness, checks, defaults, identity attributes, indexes and migration
history are semantically compatible. The string session key is included. Physical attribute
positions differ on several restored tables; replay explicitly names columns and does not depend
on their positions. PostgreSQL 18 additionally exposes NOT NULL rows in `pg_constraint`.
The compatibility checker now normalizes these differences while continuing to compare every
column's nullability and rejecting unvalidated or unenforced constraints. No production DDL was
needed for this correction. Reference: [PostgreSQL 18 catalog](https://www.postgresql.org/docs/18/catalog-pg-constraint.html).

`replication_inspect` was executed with output captured privately. Its current readiness result
is `UNSUPPORTED_SCHEMA` because migration 0002's run table and fields do not exist yet; the
separate semantic comparison shows all schema sections equal. Do not fake migrations or treat
pre-migration readiness failure as an authorization to apply them.

## Baseline findings and proposed resynchronization

Read-only SHA-256 row comparisons matched 21 of 22 approved tables. Counts were equal in all
22. The sole mismatch is the one-row `api_taskscheduler` table: only `last_execution` and
`next_execution` column value sets differ. Neither row contents nor timestamp values were printed.
All other business tables, audit logs, user/permission joins, content types and sessions matched.

These were independent repeatable-read snapshots without a verified global write fence, so they
are observations rather than a cutover consistency certificate. Repeat the full comparison under
the approved fence immediately before activation.

Smallest proposed repair, **not executed and requiring separate approval**:

1. Confirm recoverable backups/snapshots for both projects and the maintenance window. Fence all
   writers, including the local development server's business requests, provider consoles, imports
   and scheduled business jobs. Render is paused, but that alone does not establish the full fence.
2. Repeat the read-only table/column hash comparison. Confirm the same scheduler PK exists on
   both sides, exactly one row is involved, and no other columns/tables have diverged.
3. After explicit resynchronization approval, read Singapore's authoritative scheduler row privately
   and update **only** Sydney's corresponding `last_execution` and `next_execution` fields in one
   transaction. Require a PK match and an exact current target before-image; abort unless exactly
   one row is affected. Do not touch Singapore, payload logs, unrelated records or other fields.
4. Repeat all 22 table comparisons under the fence. Roll back the Sydney transaction on a failed
   guard; if verification after commit fails, retain the fence and recover from the approved snapshot
   or a separately approved corrective plan. Do not continue to capture activation with a mismatch.

There is no resynchronization DML script that is automatically executed by this preflight tool.
If any new divergence appears, revise the plan and seek approval for its actual scope first.

## Sequence behavior and disaster recovery

Read-only sequence checks examined all 21 sequence-backed approved keys on both projects.
All use cache=1, increment=1 and no cycle. Source sequence candidates are above existing source
keys. Sydney's `api_auditlogs` sequence candidate is not above the maximum copied audit ID;
the other 20 candidates are above their existing keys. No nextval/setval was called.

This target sequence difference does not block passive replication: replay preserves explicit
source IDs and never obtains business IDs from Sydney sequences. Keep Sydney fenced. Before
any future promotion, recheck and reseed **all** sequence-backed keys at or above both allocated
positions and maximum IDs under a write fence, with separate approval. This finding reinforces
why automatic promotion is disabled. Do not reseed the source outbox sequence.

Replication lag cannot currently be measured: capture is inactive and there has been no successful
replication acknowledgement. The empty outbox is not proof of equality, as the scheduler finding
demonstrates. After approved activation, use protected status plus reconciliation for health checks.

## Reviewed migration checkpoint (B3)

MigrationExecutor plans were inspected against both live databases inside read-only transactions.
Both contain **only** replication 0002 and 0003; no business migration or backwards operation is
pending in those plans. Exact operator plan commands:

```sh
python manage.py migrate replication 0003 --database=recovery --plan
python manage.py migrate replication 0003 --database=default --plan
```

Changes awaiting explicit migration approval:

* Both databases: event UUID with separate uniqueness backfill, transaction/PK/before-image/retry
  metadata, receipt digest, outstanding-event partial index and replication run history table.
* Singapore only: three capture/order/TRUNCATE functions and 66 **disabled** triggers.
* Sydney: 0003 is recorded but installs no capture functions or triggers.

After backups/window/fence are confirmed and migration approval is obtained:

```sh
python manage.py migrate replication 0003 --database=recovery
python manage.py migrate replication 0003 --database=default
python manage.py replication_inspect
```

Do not run those commands under the current read-only authorization. Re-review the plan at that
time. Django's post-migrate handlers may create content-type/permission metadata for the new run
model; inspect both sides again and ensure their IDs and rows match before activation. Do not fake
or reorder metadata to bypass a mismatch. The new schema is not active change capture.

Migration approval does not authorize trigger activation. Trigger enable requires a verified
baseline, full write fence, drained transactions, backups/rollback and a separate B4 approval:

```sh
python manage.py replication_capture enable --approved-maintenance-window
python manage.py replication_inspect --reconcile
```

Processing enablement and production POSTs must wait for approved capture and a clean baseline.

## Render and QStash preparation (not activated)

The repository Procfile runs only `gunicorn ilabcict.wsgi:application`; it does not migrate.
Live Render build/release commands and timeouts must still be confirmed before deployment.
The local requirements are installed in ignored `.venv`; requirements.txt was unchanged.
The configured database URLs need a short connection-timeout option before processor activation,
preserving all existing SSL/query options. The dedicated replication bearer token is not configured
locally and must be provisioned securely in Render/QStash before authenticated operational checks.

Prepared schedule settings, requiring a separate B6 approval:

| Setting | Proposed value |
| --- | --- |
| Destination | Verified Render HTTPS base URL + `/api/replication/process/` |
| Method / body | POST / `{}` |
| Cron | `*/5 * * * *` |
| Forwarded header | `Authorization: Bearer <dedicated replication secret>` |
| QStash API header for creation | Separate QStash API token; never the replication secret |
| Retries | 2 |
| Delivery timeout | Proposed 90 seconds, confirm against plan and measured cold-start behavior |
| Callbacks | None required |

QStash supports forwarding this bearer header via `Upstash-Forward-Authorization`; the existing
constant-time server authentication is compatible. An app JWT cannot substitute for this token.
See [schedule API](https://upstash.com/docs/qstash/api-reference/schedules/create-a-schedule).

Every five minutes gives 288 scheduled deliveries/day. Two retries can produce up to 864 attempts
per 288 messages before other schedules and retry backlogs. Upstash currently lists 1,000 daily
messages and 10 active schedules on Free; each attempt counts, and account usage remains unverified.
Its listed Free maximum HTTP response duration is 15 minutes, sufficient for a proposed 90-second
delivery timeout. [Current QStash limits](https://upstash.com/pricing/qstash).

Render documents approximately one minute to restart an idle Free service; processing's 15-second
budget starts only after the request reaches Django. Validate both worker and delivery timeout
margins. A paused service must be resumed through an approved deployment action; scheduling does
not fix intentional suspension. [Render Free behavior](https://render.com/docs/free).

## Tests and changes in B1/B2

Capture's global transaction lock still serializes approved source writers. Isolated tests verify
ordering and overlap exclusion; they do not establish production throughput or deadlock rates.
No production load test was run. Rehearse realistic transaction sizes/concurrency on disposable
copies before approving capture, and retain the existing batch/deadline limits during rollout.

* Django 6.0.4 / PostgreSQL 17.11 disposable tests: **32 passed** with psycopg 3 (41.666 seconds)
  and **32 passed** with pinned psycopg2 (40.190 seconds).
* Added regression coverage for PostgreSQL 18 NOT NULL metadata, physical column order and genuine
  nullability mismatch. Previous transaction/cascade/retry/conflict/security coverage remains.
* Replication migration dry-run check: no drift. Git whitespace checks and compilation pass.
* Local Django full system checks: no issues after duplicate URL registration removal.
* Production login, synthetic CRUD and processing requests were not performed.

Files changed during this preflight:

| File | Change |
| --- | --- |
| `api/replication/preflight.py` (new) | Reusable read-only catalog, plan, baseline and sequence diagnostics; sanitized output |
| `api/replication/schema.py` | Semantic cross-version/order compatibility; enforcement/validation checks |
| `api/replication/management/commands/replication_inspect.py` | Keep final compatibility comparison inside read-only transactions too |
| `api/replication/tests.py` | Semantic compatibility regression test |
| `ilabcict/urls.py` | Remove our redundant include; restore original root file, preserve user's corrected `api/urls.py` route |
| `api/replication/README.md` | Link current preflight and diagnostic usage |
| `api/replication/STAGE_B_PREFLIGHT.md` (new) | This checkpoint report and approval-gated repair/deployment plan |

All pre-existing user edits are preserved. No business model, service, serializer or view was changed.
The original Stage A report remains historical; its earlier duplicate-route note was superseded by
the user's corrected `api/urls.py` include and removal of our root include.

Reusable read-only commands (configured project credentials only; no credential values in output):

```sh
python -m api.replication.preflight --baseline --output .venv/stage-b-preflight.json
python -m api.replication.preflight --sequences-only --output .venv/stage-b-sequences.json
```

Baseline reads use independent read-only snapshots and are explicitly marked unfenced. These tools
do not invoke the processor or migration application. Neon poolers reject the attempted read-only
startup options; the tools instead issue SET TRANSACTION READ ONLY before inspection queries.
Local diagnostic JSON contains metadata/counts only, and is stored in ignored `.venv`.

## Rollback and manual failover

No production change needs rollback from this preflight. Code changes can be reviewed/reverted
independently of production. The future approved rollback remains: pause QStash, disable processing,
drain requests, fence writers, disable primary capture, and retain outbox/receipts. If separately
approved, reverse 0003 to 0002 to remove only capture functions/triggers. Capture gaps require a new
verified baseline before restarting; never delete events to hide a conflict.

Manual failover requires verified Singapore fencing, ingress/scheduler stop, an explicit recovery
point and accepted possible loss, Sydney snapshot/schema/sequence review, and separate routing and
promotion approval. Never enable writes on both databases. Singapore's return requires a reviewed
reconciliation/new-baseline plan, not automatic forward replay or failback. The full procedure is
in README's Manual disaster recovery and Rollback sections and is unchanged by this preflight.

**Next checkpoint:** confirm backups and a maintenance window, then review explicit approval for
the scheduler-only baseline repair and replication migrations. Trigger and schedule approvals stay
separate. Until then, all production checks remain read-only and replication stays inactive.
