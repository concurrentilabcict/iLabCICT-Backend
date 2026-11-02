# Final implementation report — 2026-11-03

The authorized implementation and preparation are complete. Production replication is **not active**.
Use [DEPLOYMENT.md](DEPLOYMENT.md) for the concise owner checklist, exact commands, conditions and
per-step rollback. Earlier Stage A/B reports remain historical snapshots.

## Fast path: bring the application online

The application code is ready for normal redeployment review with `REPLICATION_ENABLED=false`.
Pending replication migrations do not add a dependency to existing business endpoints. Replication
has no startup job, router, migration application or background thread. Full Django checks pass.
Confirm the actual Render build/release command has no auto-migrate hook; live dashboard settings
remain unverified. Render was intentionally paused by the owner and was not resumed by the agent.

You may restore ordinary Singapore application activity before replication activation. In that
case, recheck/synchronize the baseline at the later fenced cutover: those earlier writes are not
captured yet. Do not mistake application availability for an active recovery mirror.

## Features and final corrections

The existing architecture is retained: PostgreSQL capture -> transactional Singapore outbox ->
bounded Django replay -> atomic Sydney changes/UUID receipts -> Singapore acknowledgement.
All 22 approved tables remain included, including scheduler, audit/auth support and M2M tables.
Integer, string, UUID and composite keys are supported without ORM business save hooks on replay.

Final corrections within replication infrastructure:

* Whole-transaction receipt checks reject partial receipt history and validate redelivery digests.
  Receipt queries/inserts are batched once per transaction.
* Adjacent same-table INSERTs use strict bulk SQL; existing rows are never upserted. UPDATE/DELETE
  combine PK lookup and exact before-image checking in atomic DML. Interleaved operations retain
  source order, and unique/FK failures roll back the entire source transaction in Sydney.
* Monitoring separates connectivity, metrics availability, capture readiness and schema checks.
  Missing infrastructure no longer falsely reports disconnected databases. Timeouts give unknown
  compatibility, not a false assertion of mismatch. Processor activity and sanitized run codes are shown.
* Migration installation refuses active or unrelated existing capture definitions. Matching disabled
  installations are idempotent. Sydney never receives capture objects from 0003.
* PK introspection excludes INCLUDE attributes and uses logical key order. Sequence inspection uses
  a materialized key catalog so dropped-column evaluation cannot fail the lookup.
* Historical outbox error text is redacted from operator diagnostics.
* A dry-run-first, fingerprint/lock/CAS-gated scheduler bootstrap command is supplied for the owner;
  its production apply path was **not** executed.

One verification run detected a stale service revision and a dropped-column sequence-query bug.
The observed service file was preserved in ignored local artifacts, the tested fixes were reconciled,
and the final checks rerun. Final delivery is based on the corrected source, not that failed run.

## Verification

Environment: Django 6.0.4, Python 3.13.7, disposable PostgreSQL 17.11 on loopback port 55483.
Both backend suites are run with `api.replication.test_settings`, which loads no production .env
and refuses production test execution. All discovered API tests are included; business test scaffolding
itself contains no additional tests. The isolated admin fixture silences five admin-only checks;
full project system checks have zero silenced issues.

* Final full suite with psycopg 3: **60 passed**, 108.729 seconds.
* Final full suite with pinned psycopg2 2.9.12: **60 passed**, 95.667 seconds.
* Full production-settings Django system check: no issues.
* Global `makemigrations --check --dry-run`: no changes detected. No new model migration is needed
  beyond the already prepared 0002/0003; their pending initial capture SQL was corrected before use.
* Compilation, whitespace checks and tracked-business-file diff review passed.
* Full application URL/auth smoke: unauthorized status 401; temporary in-process operator-token
  status 200; disabled process POST 200 with `DISABLED` and zero applied. No persistent token was
  provisioned and no business login occurred. Status SQL ran read-only; production processing stayed off.

Coverage includes all 22 tables in one source transaction, CRUD/bulk/raw SQL, dependencies,
child-before-parent deferral, cascades, rollback, UUID/string/composite/INCLUDE keys, exact JSON
numeric precision, lost source acknowledgement after target commit, duplicate/tampered/partial
receipts, durable retry/exhaustion, concurrent capture/processors/target writers, schema/version
differences, migration reinstall guards, oversized/deadline failures, endpoint auth, monitoring,
reconciliation, read-only sequence diagnostics and scheduler repair guards/rollback.

Query-count tests verify one bulk INSERT for 25 adjacent inserts and one receipt read/write per
transaction. These are isolated measurements, **not** production throughput or latency validation.

## Production read-only findings and remaining blockers

Both configured projects connected in read-only transactions: Singapore PostgreSQL 17.11 and
Sydney PostgreSQL 18.6. All approved tables exist; semantic types/keys/constraints/indexes and
recorded migration inventories match. Physical column order and PostgreSQL 18 NOT NULL catalog
representation differ harmlessly and are normalized without weakening nullability/enforcement checks.

The refreshed read-only baseline matched 21/22 tables and equal counts in all 22. Only the one
scheduler row's `last_execution` and `next_execution` differ. Source is authoritative by the stated
primary policy and existing default-connection scheduler behavior. Snapshots were not globally
fenced, so repeat verification under the owner's actual cutover fence.

Both projects still have replication 0001 only, no user triggers, and empty outbox/receipt histories.
Actual Django **plan-only** previews ran inside read-only transactions on both: only replication
0002 then 0003, no business migration or reverse operation. No production migration was applied.
Sydney's audit sequence is behind copied IDs; explicit-ID replay is unaffected while it stays fenced,
but all sequence-backed IDs require review/reseeding before any future manual promotion.

Activation still requires owner-confirmed backups, full writer/job fencing, approved scheduler repair,
owner migrations/capture enablement, secure token and connection timeout configuration, hosting
settings/performance rehearsal, legitimate delivery verification, and owner QStash setup. The current
status endpoint can report missing metrics and unknown schema checks before migrations; this is not
a healthy activated pipeline. Lag is unmeasurable before capture, not proven zero by an empty queue.

## Files in this final review

New:

* `diagnostics.py` — safe historical error-code output.
* `scheduler_baseline.py` — narrow guarded operator repair implementation.
* `management/commands/replication_scheduler_baseline.py` — read-only plan / explicit owner apply.
* `test_finalization.py` — final regression and coverage tests.
* `DEPLOYMENT.md`, `FINAL_RESULTS.md` — final owner guide and this report.

Modified:

* `services.py` — replay optimization, receipt integrity and monitoring corrections.
* `schema.py` — correct complete/logical primary-key metadata.
* `preflight.py` — dropped-column-safe sequence inspection, read-only scheduler plan and actual
  Django migration-plan previews.
* `migrations/0003_capture_definitions.py`, `migrations/capture_v1.sql` — pre-application definition
  guards and correct PK capture. Production has not applied these files; 0001/0002 remain unchanged.
* `management/commands/replication_inspect.py`, `replication_capture.py` — error redaction and
  respect for quiet command verbosity.
* `README.md`, `STAGE_B_PREFLIGHT.md` — current-guide links and corrected behavior descriptions.

Paths above are relative to `api/replication/`. No existing business model/service/view/serializer,
authentication, scheduling, audit/broadcast, notification or WebSocket rule was modified. Review of
tracked changes shows only the preserved replication URL addition in `api/urls.py` and replication
configuration/recovery-alias changes in settings. Root URLs, requirements and Procfile are unchanged.
The original untracked replication app and unrelated user edits are preserved; no Git commit/push ran.

## Owner actions, rollback and recovery

The exact read-only previews, Sydney-first production migration commands, guarded scheduler apply,
trigger enable/disable, QStash destination/method/cron/body/header/retries/timeouts, legitimate PK/event/
receipt/ack verification and per-step rollback are in [DEPLOYMENT.md](DEPLOYMENT.md).

Source capture serializes writers and can add latency/deadlocks; a processing request occupies a web
worker. Large/slow transactions stop rather than split; limits require realistic rehearsal. HTTP
deadlines are cooperative around network/COMMIT stalls. Outbox/receipt retention is manual and
storage must be monitored. No recurring full dumps, paid worker, automatic purge or automatic
promotion/failback was introduced.

For Sydney downtime, preserve source capture/history and diagnose retries; never delete failed
heads or receipt history to force progress. For divergence, retain the fence and use a reviewed
repair. For manual failover, establish verified Singapore fencing, approve the recovery point/loss,
snapshot/reconcile/reseed Sydney, then separately approve routing to one writable primary. Keep the
old primary fenced when it returns and establish a reviewed new baseline/direction. The existing
full manual DR runbook is retained in README.

**Reserved production operations remain exclusively with the owner. Replication is not active.**
