# Stage A delivery record — 2026-11-02

Implementation is complete and inactive by default. Stage B is not authorized and has not run.
The exact approved-activation sequence, QStash setup, verification, rollback and manual DR runbook
are in [README.md](README.md). Physical production schema/trigger and baseline data compatibility
remain unverified: no Neon connections were made during Stage A.

## Files modified by this implementation

| File | Purpose |
| --- | --- |
| `api/replication/models.py` | Event UUID/transaction/PK/before-image/retry fields, receipt digest, run history, outstanding-event index |
| `api/replication/services.py` | Replace unused audit PoC with ordered, transactional, idempotent replay and monitoring |
| `api/replication/views.py` | Dedicated bearer authentication and protected fixed-purpose process/status endpoints |
| `api/replication/urls.py` | Replication endpoint paths |
| `ilabcict/settings.py` | Add only replication enable/token/batch/deadline/retry settings; preserve pre-existing recovery configuration |
| `ilabcict/urls.py` | Register `/api/replication/` before the existing api include |

## Files created

| File | Purpose |
| --- | --- |
| `api/replication/registry.py` | Explicit 22-table capture/replay allowlist and infrastructure/lock names |
| `api/replication/schema.py` | Read-only physical schema/trigger checks and streaming reconciliation |
| `api/replication/migrations/0002_infrastructure.py` | Add infrastructure fields, index and run model, with separate UUID backfill |
| `api/replication/migrations/0003_capture_definitions.py` | Reversible primary-only installation of disabled capture/order/TRUNCATE triggers |
| `api/replication/migrations/capture_v1.sql` | Frozen reusable PostgreSQL trigger functions |
| `api/replication/management/__init__.py` | Management package |
| `api/replication/management/commands/__init__.py` | Command package |
| `api/replication/management/commands/replication_capture.py` | Explicit maintenance-gated primary trigger enable/disable |
| `api/replication/management/commands/replication_inspect.py` | Read-only catalog/event-header diagnostics and reconciliation |
| `api/replication/management/commands/replication_model_inventory.py` | Offline migration-state inventory |
| `api/replication/management/commands/replication_retry.py` | Explicit requeue of a diagnosed transaction |
| `api/replication/test_settings.py` | Standalone localhost-only PostgreSQL test configuration; no .env loading |
| `api/replication/test_urls.py` | Isolated endpoint URL configuration |
| `api/replication/tests.py` | PostgreSQL integration and endpoint tests |
| `api/replication/README.md` | Architecture, configuration, Stage B sequence, QStash, DR, rollback and risks |
| `api/replication/INVENTORY.md` | All approved primary keys, sequences, uniqueness and relationships |
| `api/replication/STAGE_A_RESULTS.md` | This delivery record |

The existing replication `0001_initial.py`, package initializers and empty `serializers.py` were
preserved. No existing business file was edited by this implementation. An additional concurrent
change appeared in `api/urls.py` while work was in progress and was left untouched. It adds
`api/replication/` inside the existing `/api/` prefix, creating an extra `/api/api/replication/`
alias; the canonical requested endpoints are registered separately in `ilabcict/urls.py`.

Ignored local verification artifacts: `.venv/` contains Django 6.0.4, disposable PostgreSQL cluster
files/logs and Python caches. Neither production settings nor production records were used for
test database setup. The local PostgreSQL server was stopped after verification.

## Architecture delivered

Source transaction lock -> database row capture -> durable Singapore outbox -> bounded HTTP
processor -> atomic Sydney DML plus UUID/digest receipts -> source acknowledgement.
Whole source transactions preserve dependency ordering; retries never skip a blocked head.
Before-image/PK/unique checks stop divergence rather than overwriting unrelated target rows.
Monitoring is protected and never equates an empty queue with consistency. Reconciliation is a
separate read-only operator operation. Failover remains entirely manual and requires fencing.

## Verification executed

Environment: Windows, Python 3.13.7, Django 6.0.4, PostgreSQL 17.11, two disposable local test
databases on `127.0.0.1:55483`. Final test runs:

| Verification | Result |
| --- | --- |
| Full suite with pinned psycopg2 2.9.12 (psycopg 3 import disabled for this process) | **31 passed**, 40.329 seconds |
| Full suite with psycopg 3.3.6 selected by Django | **31 passed**, 58.887 seconds |
| `makemigrations replication --check --dry-run --settings=api.replication.test_settings` | No model/migration drift |
| `git diff --check` | Passed |
| `python -m compileall -q api/replication` | Passed |
| Offline migration-state inventory generation | Passed; 22 approved tables |

Each suite created, migrated and destroyed only the isolated test databases. Production settings
are forbidden by the test module before database setup. The isolated settings intentionally silence
five admin-only checks because the suite has no admin middleware/template authentication context;
the test system check otherwise reports no issues. Full production app regression tests and live
Neon/Render/QStash delivery tests were not performed.

Coverage includes INSERT/UPDATE/DELETE, unchanged updates, bulk and direct SQL, source rollback,
multi-table FK transactions, ORM cascading deletes, M2M joins, string/UUID/composite keys,
primary-key changes, exact JSON numeric precision, duplicate delivery/lost acknowledgement,
tampered receipt rejection, target transaction rollback, unrelated-row conflicts, durable retry
and exhaustion, overlapping processor exclusion, concurrent capture ordering, recovery outage,
business/infrastructure schema drift, capture-definition drift, unsafe sequence caching,
oversized transactions, deadline rollback, unauthorized/missing-secret requests, disabled processing,
rejected HTTP parameters, authenticated monitoring, sanitized operator diagnostics and divergence
detection. UUID/composite tests modify only disposable schema fixtures and restore them afterward.

## Changes awaiting Stage B approval

1. Read-only production catalog review and a verified consistent data baseline under a write fence.
2. Apply replication 0002/0003 on Sydney and Singapore after migration-plan review/backups.
3. Approve and activate 66 primary triggers (three per approved table); none on Sydney.
4. Verify row reconciliation; explicitly enable processing in Render and validate delivery.
5. Separately approve/create the five-minute QStash schedule with the dedicated forwarded token.

No production migration, trigger install/activation, schedule, data modification, credential
change, routing change or failover action has been performed. See README's **Exact Stage B
activation sequence** for ordered commands and stop conditions; do not run them before approval.

## Principal risks and limits

* Capture serializes approved source write transactions. Measure latency and deadlocks under the
  real workload before activation; outbox unavailability can fail source writes.
* Oversized/slow source transactions block safely rather than splitting. HTTP work uses cooperative
  deadlines, database timeouts and bounded event counts, not a guaranteed hard network deadline.
* Sydney fencing is an operational prerequisite; no automatic routing, promotion or reverse stream
  exists. Promotion requires reviewed sequence reseeding and explicit acceptance of possible loss.
* Production baseline, roles, installed triggers, capacity and delivery cold starts remain unverified.
  Legacy audit-only events must be diagnosed explicitly before processing can start.
* Outbox/receipts contain sensitive data and have no automatic retention purge. Replication excludes
  external files, sequence state, DDL and uncaptured objects. Empty-queue status cannot prove equality.

Stage A stops here pending explicit user approval for Stage B.
