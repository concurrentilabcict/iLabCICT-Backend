# iLabCICT replication infrastructure

Use [DEPLOYMENT.md](DEPLOYMENT.md) for the final, owner-executed activation checklist and guarded
scheduler reconciliation commands. [FINAL_RESULTS.md](FINAL_RESULTS.md) records final verification.
[STAGE_A_RESULTS.md](STAGE_A_RESULTS.md) and [STAGE_B_PREFLIGHT.md](STAGE_B_PREFLIGHT.md) are historical
checkpoints. No production replication activation has been performed.

## Safety and inspection findings

Stage A created code only. Later preflight connected to Neon exclusively for read-only inspections;
no production migration, trigger installation/activation, schedule creation, promotion, credential
change or production record write was performed by the agent.
`REPLICATION_ENABLED` defaults to false. There is no startup job, thread, signal handler,
database router or automatic failover. The existing application continues using `default`.

The existing uncommitted settings changes (replication app registration and recovery connection)
are preserved. The existing replication 0001 migration is unchanged. Its audit-only proof-of-concept
processor had integer event IDs but UUID receipts, per-event commits, and no durable retry policy.
No business code calls those helpers; they were replaced within replication/services.py.
Existing business services, models, views, serializers, signals and responses were not edited.

Repository inspection found one api migration leaf, `0053_alter_room_status`, and replication
`0001_initial`. No earlier trigger-installing migrations were found. Read-only preflight subsequently
verified matching semantic schemas, no user triggers, empty replication histories and one scheduler
timestamp mismatch. See the final report; repeat verification under the actual maintenance fence.
Matching migration inventories alone do not prove equal rows.
The existing Procfile only starts Gunicorn. Existing `.github/workflows/scheduler.yaml` is a
separate business scheduler; it is untouched and must be fenced during DR/maintenance.

The explicit allowlist has 22 tables, including all 14 business tables, both user M2M tables,
authorization/content-type dependencies, admin logs, and sessions. See [INVENTORY.md](INVENTORY.md)
for keys, unique constraints and FK relationships generated offline from migration state.
Most tables have sequence-backed IDs; `django_session.session_key` is a string primary key.
Capture and replay discover complete primary-key columns rather than assuming `id` or integers.
The current schema has no UUID or composite business primary keys, but SQL capture and predicates
handle those key shapes. New tables require a reviewed migration and allowlist update.

Excluded: every `replication_*` infrastructure table, `django_migrations`, PostgreSQL catalogs,
sequences themselves, and external Cloudinary files. No other public table is implicitly approved.
Unknown public tables or user triggers stop processing pending review. Runtime business models are
spread across subpackages; offline inventory uses migration state so URL import order cannot omit them.

## Architecture and guarantees

`0002_infrastructure` adds per-event UUID, transaction ID, complete PK JSON, before-image, retry
deadline, receipt digest and a run history table. UUIDs are backfilled separately before applying
uniqueness, preserving any existing event status/payload. Legacy audit-only events have no valid
transaction metadata: inspect and resolve them before activation. They deliberately block replay;
there is no automatic conversion, deletion or overwrite.

`0003_capture_definitions` installs frozen SQL functions and **disabled** triggers on `default`
only. On `recovery` its database operation is a no-op, while its migration is recorded normally.
Installing this migration does not start capture. A matching disabled installation is idempotent;
active capture and unrelated existing definitions are refused before replacement. Activation is a distinct
maintenance command. All source and target migrations must match before processing.

The BEFORE STATEMENT trigger takes transaction advisory lock `73481001` on each approved DML
statement. The AFTER ROW trigger writes before/after JSONB and PKs to the outbox, with
`pg_current_xact_id()` and an independent random UUID. Unchanged updates produce no event.
TRUNCATE is rejected while capture is enabled. Events roll back with their source transaction.
The trigger uses invoker privileges, qualified objects and a fixed search path; it has no dynamic SQL.

The capture lock is held until commit. Therefore all events from a captured transaction precede
the events of the next captured transaction, regardless of UUID, transaction-ID assignment, or
application-ID ordering. Outbox sequence CACHE=1, INCREMENT=1, NO CYCLE is checked explicitly.
Gaps from rollbacks are harmless; no high-water cursor skips invisible transactions. Never reseed
the source outbox sequence or grant clients permission to bypass capture. Sequence order **alone**
would not provide this guarantee. All writers, including raw SQL, must use enabled origin triggers.

The processor takes a different transaction advisory lock (`73481002`) on Singapore. It reads
the earliest unapplied transaction, never skips a blocked head, and never splits a source
transaction to fit the batch. Sydney takes its own transaction advisory lock as well, covering
an in-flight apply if the source connection disappears. All rows and event receipts for one
source transaction commit atomically in Sydney, with deferred FKs checked before commit.
Within a transaction it replays source event order, including Django collector cascades and M2M
operations. Only adjacent INSERTs on the same table are batched; updates/deletes retain exact order.
SQL replay bypasses Django save methods, notifications, audit services and broadcasts.

INSERT requires an absent PK; even an identical existing row without a receipt is a conflict.
UPDATE/DELETE include the exact entire before-image in their atomic DML predicate. Unique/FK violations halt the stream.
There is no upsert and no last-writer-wins overwrite. Receipt digests reject reusing a UUID
with changed content. Native JSON text is passed intact to PostgreSQL typed records, avoiding
Python float rounding of JSON or numeric data. Values are parameters; identifiers come from
the allowlist and verified catalogs. HTTP callers cannot specify events, tables, SQL or limits.

Singapore acknowledges only after Sydney commits. A crash after target commit leaves source
events pending; receipts make redelivery safe. A source acknowledgement outage may roll back
multiple source acknowledgements while corresponding target transactions remain committed.
Those receipts remain valid and replay resumes from the earliest unacknowledged transaction.
Receipts are read/inserted once per transaction. An incomplete receipt set is treated as corruption
and blocks the stream; it is never used to replay a partial source transaction.
This is at-least-once delivery with one committed target effect per UUID, not a distributed commit.

Transient connection, deadlock, serialization, lock and timeout failures retry with durable
exponential delay (60 seconds initially, capped at one hour), up to the configured attempts.
SQL errors, malformed payloads, schema drift and row conflicts stop instead of skipping data.
Run/event diagnostics contain stable error codes, never exception text or row payloads.
Operator retry, after investigating the cause:

```sh
python manage.py replication_inspect --events
python manage.py replication_retry TRANSACTION_ID --conflict-resolved
```

This resets retry bookkeeping for that transaction only. It does not change its data or receipts.
Do not delete a failed head to unblock later events. Repair the baseline through a separately
reviewed recovery procedure, then retry, or establish an entirely new verified baseline.

## Configuration and endpoints

```text
REPLICATION_ENABLED=false
REPLICATION_TOKEN=<independent secrets.token_urlsafe(32) value; at least 43 characters>
REPLICATION_BATCH_SIZE=200
REPLICATION_TIME_BUDGET=15
REPLICATION_MAX_ATTEMPTS=8
```

The token must be independently random (at least 256 bits), stored in Render/QStash secrets,
sent only over HTTPS, and excluded from access logs and screenshots. It is not the QStash API
token, scheduler token or application JWT secret. Authentication fails closed if absent/short.
Both endpoints require `Authorization: Bearer <REPLICATION_TOKEN>` and return `Cache-Control: no-store`:

* `POST /api/replication/process/` accepts only an empty body or `{}` and no query parameters.
  Returns counts, outcome, duration and a sanitized code on failure. Busy/disabled runs return
  200 without work; retry/unavailability returns 503; blocked streams return 409.
* `GET /api/replication/status/` reports connectivity, pending/failed count, oldest outstanding age,
  latest source acknowledgement, latest run duration/outcome/error code, compatibility/readiness
  and processor-lock activity. Missing infrastructure does not imply a failed database connection.
  The status result is informational; unreachable components appear false/unknown.

Metrics expose neither secrets nor rows. `replication_lag_seconds` is the age of the oldest
unacknowledged event, not a measurement of commit-to-commit latency. It is null for an empty
queue, which does **not** prove consistency. An unreachable Singapore yields no trustworthy
pending count. `consistency_verified` always remains false on this lightweight endpoint.
`metrics_available` distinguishes complete infrastructure metrics from unknown values.
`schema_compatible` is null when checking could not finish, false for a known structural conflict,
and true for compatible schema. `capture_ready` separately checks whether source capture is enabled.

Catalog checks compare named columns/types/defaults/nullability, PK/FK/unique/check constraints, indexes, and
migration history. They reject missing/new tables, partitions, RLS, generated columns, unknown
triggers, wrong capture function bodies/timing, disabled capture and target-side user triggers.
Identities are supported and explicitly preserved. These checks do not prove business data equality.
Physical attribute order and PostgreSQL 18's duplicate NOT NULL catalog representation are normalized;
actual nullability differences and unenforced/unvalidated constraints continue to block processing.

Batch size is clamped to 1..1000 and time budget to 1..20 seconds. Configure both existing
database URLs with a short `connect_timeout=3` query option (preserving sslmode and other options)
before activation. Existing database settings are not overridden. Query/lock timeouts and a
monotonic deadline bound normal work; this is a cooperative deadline, not a hard wall-clock
guarantee under DNS/network stalls or a slow COMMIT. Set Render/Gunicorn and QStash delivery
timeouts above budget plus connection/commit margin. Verify the available QStash plan's timeout
against measured Neon cold-start behavior. Do not increase work until it exceeds the HTTP timeout.
No background worker is required; each authorized HTTP request performs bounded work synchronously.

## Isolated verification

Tests must use the standalone `api.replication.test_settings`. It never imports production settings
or loads `.env`, uses only `127.0.0.1:55483`, user `replication_test`, and two named test databases.
The test module refuses other settings before Django's test database setup. **Never run this suite
with production settings.** PostgreSQL 14+ is required by the capture SQL; verified locally on 17.

Example Windows setup (a disposable cluster inside ignored `.venv`; no production credentials):

```powershell
python -m venv --system-site-packages .venv
./.venv/Scripts/python.exe -m pip install Django==6.0.4
& 'C:/Program Files/PostgreSQL/17/bin/initdb.exe' -D .venv/replication-pg -U replication_test -A trust --encoding=UTF8 --locale=C
& 'C:/Program Files/PostgreSQL/17/bin/pg_ctl.exe' -D .venv/replication-pg -l .venv/replication-pg/server.log -o '-h 127.0.0.1 -p 55483' -w start
./.venv/Scripts/python.exe manage.py test api.replication --settings=api.replication.test_settings --noinput
./.venv/Scripts/python.exe manage.py makemigrations replication --check --dry-run --settings=api.replication.test_settings
& 'C:/Program Files/PostgreSQL/17/bin/pg_ctl.exe' -D .venv/replication-pg -m fast -w stop
```

Full requirements remain those in the repository. The Stage A test environment uses installed
dependencies plus the project's pinned Django version. Test databases are created/migrated and
destroyed locally; no production rows are used. Both psycopg 3 and the pinned psycopg2 driver
should be exercised. See STAGE_A_RESULTS.md for actual execution results and scope.

Offline, without any connection:

```sh
python manage.py replication_model_inventory --settings=api.replication.test_settings --skip-checks
```

## Exact Stage B activation sequence — requires separate approval

The final owner-executed procedure is [DEPLOYMENT.md](DEPLOYMENT.md). It includes the guarded
scheduler-only repair, post-migrate baseline checkpoint, per-step rollback and exact QStash fields.
The sequence below remains architectural context; use the final checklist for the handoff.

These steps are instructions, not actions performed by Stage A. Obtain explicit approval for
production migrations, trigger activation and QStash scheduling before their respective steps.

1. Review this implementation, inventory, risks, PostgreSQL version, permissions and workload.
   Rehearse on isolated Neon branches or PostgreSQL copies first. Record throughput and latency
   under concurrent business writes; approve the capture serialization tradeoff.
2. Set `REPLICATION_ENABLED=false` in Render. Deploy the code. Confirm Render has no build/release
   auto-migrate command; the repository Procfile itself does not migrate. Generate/store the token.
   Restrict database access: Sydney's application/admin/business-scheduler credentials must not
   permit ordinary writes. Only the replication operator/connection can write there. Do not run
   an application or business scheduler against Sydney. Preserve one writable Singapore primary.
   The source application connection must be permitted to INSERT into the outbox and use its
   sequence; the processor must SELECT/UPDATE outbox bookkeeping and INSERT run history. The
   recovery connection needs DML rights on approved tables and INSERT/SELECT on receipts.
   Migration/capture installation requires the table owner or an appropriately privileged operator.
   Review these grants explicitly; no command in this implementation changes roles or credentials.
3. Run `python manage.py replication_inspect` in the approved environment for read-only catalogs.
   Archive the output in restricted operator storage. Inspect all existing triggers, outbox legacy
   events and migration differences. A missing 0002 schema is expected at this point; do not
   interpret an inspection error as permission to migrate. Review pending plans:

   ```sh
   python manage.py migrate replication 0003 --database=recovery --plan
   python manage.py migrate replication 0003 --database=default --plan
   ```

   Stop if the plan includes unexpected business migrations. Do not use `--fake` to bypass drift.
4. Fence every business writer (Render web/admin, business scheduler, direct SQL/import jobs).
   Drain active write transactions. Take recoverable snapshots/backups of both databases.
   Verify the known synchronized baseline using a consistent, read-only comparison; resolve
   every difference through a separately approved synchronization plan. Inventory equality is
   insufficient. Keep the write fence through step 7, avoiding an uncaptured baseline gap.
5. After migration approval, run these exact migration commands:

   ```sh
   python manage.py migrate replication 0003 --database=recovery
   python manage.py migrate replication 0003 --database=default
   python manage.py replication_inspect
   ```

   Expect new replication columns/table on both, and 66 **disabled** triggers plus three functions
   on Singapore only. Confirm no capture functions/triggers in Sydney. Verify post-migrate
   content-type/permission rows also match. Resolve legacy outbox records explicitly; do not
   automatically mark them applied. Keep `REPLICATION_ENABLED=false`.
6. After trigger-activation approval, while writers remain fenced:

   ```sh
   python manage.py replication_capture enable --approved-maintenance-window
   python manage.py replication_inspect --reconcile
   ```

   Enable is atomic across all tables and takes exclusive table locks with a timeout. It checks
   schema compatibility but relies on the operator's baseline verification. Reconciliation must
   report every table matching and an empty outstanding queue. Any mismatch stops deployment.
7. Set Render `REPLICATION_ENABLED=true`, leave Sydney fenced, and redeploy. Release **Singapore**
   business writers only after capture is verified. Perform an authenticated process request:

   ```sh
   curl --fail-with-body -X POST "$API_BASE_URL/api/replication/process/" -H "Authorization: Bearer $REPLICATION_TOKEN" -H 'Content-Type: application/json' -d '{}'
   curl --fail-with-body "$API_BASE_URL/api/replication/status/" -H "Authorization: Bearer $REPLICATION_TOKEN"
   ```

   Use existing legitimate source activity for production verification. Perform synthetic CRUD,
   rollback and destructive cases only on isolated databases, as in the test suite. Monitor queue
   growth, failures, cold starts and response time; at a quiet point run reconciliation again.
8. After explicit schedule approval, create a QStash schedule for the exact HTTPS process URL,
   method POST, body `{}`, cron `*/5 * * * *` (UTC; the five-minute interval is timezone-independent).
   Set the forwarded Authorization header to the dedicated replication token and delivery timeout
   above measured processing duration within the available plan. Choose bounded QStash retries
   (for example 2); durable outbox retries remain authoritative. Disable request-header logging.
   Use Upstash Console or the official schedules API, whose request uses
   `Upstash-Forward-Authorization: Bearer <REPLICATION_TOKEN>`. The QStash API's own
   `Authorization` is its separate QStash API token. No schedule was created by this work.

Official references: [QStash schedules API](https://upstash.com/docs/qstash/api-reference/schedules/create-a-schedule),
[QStash schedules](https://upstash.com/docs/qstash/features/schedules),
[PostgreSQL trigger semantics](https://www.postgresql.org/docs/17/sql-createtrigger.html).

## Reconciliation and operations

`python manage.py replication_inspect` runs catalog reads under read-only transactions; it prints
metadata only, never connection settings or row payloads. Errors may include catalog names in the
operator console; keep output private. HTTP responses deliberately contain less information.

`python manage.py replication_inspect --reconcile` is also read-only. It takes the source capture
transaction lock (briefly blocking captured writers), requires an empty outstanding queue and
compatible active capture, and compares sorted SHA-256 row hashes and counts under consistent
read-only snapshots. It streams hash results instead of loading rows into application memory.
It reports table matches/counts only. Keep target external writers fenced throughout. A nonempty
queue refuses comparison rather than mistaking expected lag for corruption. Per-query 30-second
and lock two-second limits protect traffic; a full reconciliation may exceed HTTP budgets, so it
is an operator command only. For large tables use a scheduled maintenance window and database
capacity planning; this implementation does not provide incremental/chunk-range reconciliation.
Hashes give strong diagnostic confidence, not a mathematical proof or an audit of external files.

Alert on inaccessible primary/recovery, FAILED events, growing oldest age, incompatible schema,
repeated non-OK runs and sustained queue growth. An empty queue during a source outage is unknown,
not healthy. Keep source outbox and Sydney receipts until a separately approved paired retention
policy exists. Deleting receipts can make acknowledgement-loss replay unsafe. No automatic purge
is installed. Track storage quotas because full row before/after images include sensitive data,
password hashes, session contents, notification data and reset-token hashes.

Schema deployment after activation requires a write fence and processor disable, matching
migrations on both databases, catalog review, baseline verification and restart. Do not mutate
tables while replaying queued events whose row shape belongs to the previous schema. Drain first.

## Manual disaster recovery

1. Detect/confirm the Singapore outage from infrastructure monitoring and replication status.
   Do not promote automatically. Freeze ingress, Render web/admin writes, the existing scheduler,
   QStash schedule and any external writers. Set `REPLICATION_ENABLED=false` and stop/drain
   active requests. Keep Sydney closed to application writes until this procedure is approved.
2. Fence Singapore at the provider/network/role level so it cannot accept writes if it returns.
   An unavailable host is not proof it is fenced. Require an operator to verify this fence before
   changing any application database URL. If fencing cannot be established, do not promote.
3. If Singapore is readable, inspect pending/failed counts, oldest event and last acknowledgement;
   drain through the processor only if safe and explicitly approved, then stop it again. Reconcile
   at the fence with no outstanding events. If Singapore is inaccessible, pending count and the
   final source commit position are unknown. Sydney receipts show what arrived, not what was lost.
4. Record the latest verified acknowledgement/reconciliation time and the available Sydney receipt
   history. Explicitly approve the recovery point and possible loss of all unavailable/unapplied
   Singapore transactions. The five-minute schedule is **not** a five-minute RPO guarantee: cold
   starts, failures, queue backlog and oversized transactions can extend loss exposure indefinitely.
5. Snapshot Sydney before promotion. Verify schema and constraints. Reseed every sequence-backed
   business ID on Sydney at or above both its current allocated sequence position and maximum
   replicated key, while all writes remain fenced. Explicit-ID replay intentionally does not
   advance business sequences. Use Django's `sqlsequencereset` output only as a starting point:
   review it against INVENTORY.md (including auth/admin and auto-created M2M sequences), and ensure
   it never lowers a sequence's current position. Sequence changes require separate approval and
   are not executed by any replication endpoint/command. String/UUID keys need no sequence reset.
6. After explicit promotion approval and verified Singapore fencing, an operator manually changes
   Render's active `DATABASE_URL` to Sydney and grants only the new primary the needed business
   write access. Keep replication disabled and the old source URL/config archived securely.
   The recovery alias must not point back to the promoted database for processing. Smoke-test
   business access, then release ingress/scheduler against this one primary only. Record the
   exact promotion timestamp and accepted recovery point. No automatic routing exists here.
7. When Singapore returns, keep it fenced. Do **not** resume the old forward queue: Sydney now
   owns writes and no reverse capture was established. Snapshot both, preserve unapplied source
   events for forensic recovery, compare differences and resolve conflicts under a separate
   approved plan. Usually establish a fresh consistent baseline from the promoted Sydney primary
   into a new recovery database, review lost source-only operations manually, and configure a new
   replication direction in a separate change. UUID receipts from the old stream must not be
   treated as evidence of new baseline consistency. Switching back requires another maintenance
   fence, verified baseline/sequence positions, explicit routing changes and promotion approval.

## Rollback and limitations

First pause QStash, set processing disabled and drain in-flight requests. Under a write fence run
`python manage.py replication_capture disable --approved-maintenance-window`. Existing business
tables/records and prior schema are unchanged. Capture downtime loses change tracking: restarting
later requires a fresh verified baseline, not simply toggling the flag back on.

To remove capture definitions after backup/review and separate migration approval:

```sh
python manage.py migrate replication 0002 --database=default
python manage.py migrate replication 0002 --database=recovery
```

This reverses 0003, removes only its triggers/functions and retains the infrastructure data.
Keep 0002 and receipts for diagnosis. Reversing 0002 drops new infrastructure columns/history;
do not do so casually, and never reverse 0001 or remove business tables to roll this work back.
Remove the replication URL include/config only after operational shutdown if rolling code back.

The global capture lock trades write concurrency for auditable transaction order and can add
latency/deadlocks when applications acquire other locks first. Long transactions delay all captured
writes. Measure on realistic load before production approval. Source capture fails closed if the
outbox cannot be written; storage exhaustion can therefore fail business writes. Whole source
transactions exceeding the server batch limit block with TRANSACTION_TOO_LARGE; smaller ones may
exceed the HTTP time budget and require an approved larger bounded window or separate operator
recovery tooling. No source transaction is silently split or skipped.

Only origin INSERT/UPDATE/DELETE are supported. TRUNCATE, unreviewed DDL, trigger disabling,
`session_replication_role=replica`, writes by privileged owners bypassing policy, changing the
outbox sequence, or uncaptured tables can invalidate guarantees. Restrict operational access.
Sydney must have exclusive replication writers until manual promotion; before-image checks cannot
replace provider/role fencing. Unexpected source/target triggers, RLS, generated columns and
partitioned tables deliberately stop processing until reviewed. Target sequence state and external
object files are not replicated. External notifications and scheduled executions are not replayed.
This system provides asynchronous recovery, not synchronous durability, automatic promotion,
global distributed transactions, or guaranteed failover without data loss.
