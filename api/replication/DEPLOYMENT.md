# Final operator deployment guide

Prepared 2026-11-03. All production-changing commands below are **for the owner to execute**.
The agent has not applied production migrations, reconciled records, activated capture/processing,
created a QStash schedule, changed roles/routing or performed a production login.

## Two separate readiness decisions

**Application redeployment with replication disabled:** the source is ready for the normal deployment
review. Django checks pass; business code is unchanged; no replication startup hook or automatic
migration exists. Keep `REPLICATION_ENABLED=false`. Confirm the actual Render build/release command
does not run migrations automatically. Render dashboard settings remain owner-verified prerequisites.
Resuming ordinary business use before the later cutover is possible, but every new uncaptured write
must be included in a fresh baseline at that cutover. No claim is made about a hosted deployment.

**Replication activation:** not yet approved or active. The one scheduler row differs in
`last_execution` and `next_execution`; both production databases still have only replication 0001.
Backups, the global write fence, live hosting settings, secrets and performance rehearsal must be
confirmed by the owner. All 22 approved tables, including the scheduler, remain in scope.

## Concise activation checklist

Follow the detailed conditions below; do not skip the fence between steps 2 and 7.

1. Ship all replication source files, migrations **and `capture_v1.sql`** with the normal app deploy.
   Keep processing disabled. Confirm no auto-migrate build/release hook; provision the dedicated token
   and short DB connection timeouts securely. Do not change existing business configuration/routing.
2. Establish the maintenance window: stop all business writers and scheduled report calls, take and
   verify recoverable backups of **both** databases, and drain active write transactions. Fence Sydney
   from ordinary business writes throughout normal operation. A paused Render service alone is not a
   complete fence: local servers, imports, SQL consoles and external jobs also count.
3. Run the read-only baseline and scheduler plan below. If the only difference is still the reviewed
   scheduler timestamps, execute the guarded scheduler repair **yourself**, with fresh fingerprints
   and backup/window confirmations. If scope changed, stop and revise the repair plan. Verify all 22
   tables match; do not exclude `api_taskscheduler` or ignore timestamps.
4. Review both read-only migration plans. Run **Sydney's migrations first**, then **Singapore's**.
   Stop on unexpected business operations or history differences; never use `--fake`.
5. Inspect both databases: matching schema/history and baseline; Singapore has three functions and
   66 disabled triggers, Sydney has no capture triggers/functions. Recheck post-migrate auth/content
   metadata too. Keep processing disabled and all writers fenced.
6. Execute the capture-enable command yourself. Reconcile immediately; all 22 tables must match
   and the outstanding queue must be empty. Never release writers while capture is still disabled.
7. Set processing enabled in Render and redeploy/restart the app under the fence. Leave Sydney
   fenced. Permit **one controlled legitimate source operation** for the verification below; process
   it and confirm its original PK, whole transaction receipts and source acknowledgement.
8. Configure QStash yourself using POST, `{}`, `*/5 * * * *`, the dedicated forwarded bearer and
   bounded retries/timeouts below. Confirm delivery logs and sanitized process results.
9. Resume normal Singapore activity and scheduled business jobs. Keep Sydney's ordinary writers
   fenced. Watch pending/failed counts, oldest age, run errors, storage and HTTP duration.
10. Reconcile at a quiet point or maintenance fence. Retain the manual recovery runbook and test
    recovery separately. Do not enable automatic failover or reverse replication.

## Read-only preparation and baseline checkpoint

Use a trusted environment with the existing `DATABASE_URL` / `RECOVERY_DATABASE_URL` configuration.
Do not paste credentials into commands, reports or chat. Commands run equally from a trusted local
virtual environment; a paid Render background worker or dashboard shell is not required.
The `python` examples assume the project's environment is active. In this Windows checkout use
`.\.venv\Scripts\python.exe` in place of `python`; the global interpreter had a different Django
version. Verify Django 6.0.4 before running any owner migration. Use the existing pinned requirements.

Read-only, no data or schema changes:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python -m api.replication.preflight --baseline --output .venv/preflight.json
python -m api.replication.preflight --sequences-only --output .venv/sequences.json
python -m api.replication.preflight --scheduler-plan --output .venv/scheduler-plan.json
```

The diagnostic module enforces read-only transactions and prints metadata/counts/fingerprints only.
Without a global write fence, its independent snapshots are observations, not a cutover certificate.
The `.venv/` output directory must exist and is ignored by Git. Keep diagnostic files private.
Ordinary `makemigrations --check --dry-run` writes neither migration files nor database records.

Singapore is authoritative because it is the designated normal primary and the existing scheduler
uses the default ORM connection. No failover has been authorized. The baseline helper copies stored
timestamps exactly; it does not invoke scheduling calculations, reports, audits or broadcasts.

Important scheduler fence: the existing **GET `/api/scheduler/reports/` performs writes**, including
an audit entry even when no report is due. Pause external callers to that route. Do not use it as a
read-only health check. Also fence the scheduler create/update routes and any direct SQL writers.
The repository's current GitHub workflow merely prints a date; inspect actual external QStash/jobs
separately instead of assuming that workflow is the only scheduler. No business scheduler code was changed.

## Minimal scheduler repair — owner only, production DML

First run this default **read-only** plan in the approved window with processing disabled:

```sh
python manage.py replication_scheduler_baseline
```

Expected result: one row on both sides, the same PK and all non-timestamp fields, with only the two
reviewed execution fields listed as different. The output gives source/target SHA-256 fingerprints,
not row contents. Empty differences mean no repair is needed; move on to the full baseline check.

Only after reviewing that result and confirming backups/window, replace the placeholders below
with the **fresh** plan's fingerprints and execute this **yourself**:

```sh
python manage.py replication_scheduler_baseline --apply --expected-source SOURCE_FINGERPRINT --expected-target TARGET_FINGERPRINT --backup-confirmed --approved-maintenance-window
```

This is the only new reconciliation command with a write path. It is not called by any endpoint,
startup code or preflight. It writes only Sydney's `last_execution` and `next_execution`, with:

* Processing disabled; capture absent/disabled; no outbox or receipt history on either database.
* Matching reviewed schemas and exactly one scheduler row with the same PK.
* No differences outside those two fields and matching current plan fingerprints.
* A source scheduler table lock, a target scheduler write lock, processor exclusion, timeouts and
  a full target before-image compare-and-swap.
* Exactly one affected row and a matching after-image before target commit; verification failure
  rolls back that target transaction. A second dry run of a completed repair reports no differences.

The flags record operator confirmations; they do not prove provider backups or a global write
fence. The tool internally freezes only the scheduler table, so the global fence is still mandatory.
It deliberately refuses multiple rows, other field differences, enabled capture or an existing
replication history. It is a bootstrap tool, not a recurring resynchronization service.

Repeat the full read-only comparison afterward. If other records differ, do not use this command
to conceal them; prepare a separately reviewed repair. There are no recurring dumps/restores.

Rollback: failed preconditions/verification automatically roll back. After a successful commit,
keep the fence and use the verified recovery snapshot or a separately approved before-image repair
if needed; do not blindly overwrite records after normal writers resume. A lost client response can
be resolved with another read-only plan, without repeating an unverified write.

## Production migrations — owner only, correct order

Read-only previews:

```sh
python manage.py migrate replication 0003 --database=recovery --plan
python manage.py migrate replication 0003 --database=default --plan
```

The reviewed plans contain only `replication.0002_infrastructure` and
`replication.0003_capture_definitions`. The Python operations are opaque in the plan output: review
those files and the frozen SQL asset too. 0002 adds infrastructure fields, a partial queue index and
run history. It backfills event UUIDs separately before enforcing uniqueness. The current live
outbox is empty; legacy entries, if they appear later, require diagnosis rather than deletion.

**Sydney — modifies production schema; execute yourself after approval/backups/fence:**

```sh
python manage.py migrate replication 0003 --database=recovery
```

**Singapore — modifies production schema and installs disabled capture; execute yourself next:**

```sh
python manage.py migrate replication 0003 --database=default
```

No business model/constraint change is included. 0003 does nothing to Sydney's capture objects;
it installs three functions and three disabled triggers on each of Singapore's 22 tables.
Installation refuses active capture or unrelated existing trigger/function definitions before
replacing anything. A matching disabled installation can be repeated safely in an isolated rehearsal;
do not manually rerun migration internals to reconfigure an active stream.

Django post-migrate can create the new run model's content-type/permission metadata. Verify those
rows and IDs match on both sides before activation. The agent has not applied these migrations.

Verify, read-only:

```sh
python manage.py replication_inspect
python -m api.replication.preflight --baseline --output .venv/post-migration-baseline.json
```

Source trigger headers must show 66 entries with state `D`; recovery must show none. In each
project's SQL console, this optional read-only query lists the capture functions independently:

```sql
SELECT n.nspname, p.proname
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public'
  AND p.proname IN ('ilab_replication_order','ilab_replication_capture','ilab_replication_no_truncate')
ORDER BY p.proname;
```

Expect three rows only in Singapore, none in Sydney. Metadata compatibility alone never proves
row consistency. Do not release writers until the full baseline and activation checks pass.

Rollback: a failed individual migration is transactional; earlier successfully committed migrations
may remain. Keep processing/capture off, retain the fence and inspect both histories. To remove
0003's capture definitions, preview reversing it to 0002 on both sides, then execute the reviewed
reversal yourself. Retain 0002/outbox/receipts for diagnosis. Do not drop the replication tables
while source capture still refers to them, and do not reverse business migrations or use `--fake`.

## Trigger activation — owner only

Prerequisites: fresh matching baseline, verified snapshots, all writers fenced, active transactions
drained, Sydney ordinary writers fenced, matching migrations and installed disabled definitions.
Keep processing disabled for this command:

```sh
python manage.py replication_capture enable --approved-maintenance-window
python manage.py replication_inspect --reconcile
```

The enable command takes processor exclusion and exclusive locks on every approved source table,
then enables all triggers atomically. It times out if it cannot obtain locks. It does not verify the
external fence or create a baseline for you. The following reconciliation is read-only and must
show all tables matching with no outstanding events. Capture and replay are separate controls.

For activation rollback before releasing writers, keep processing off and execute yourself:

```sh
python manage.py replication_capture disable --approved-maintenance-window
```

If writers operate while capture is off, a fresh verified baseline is required before restarting.
Do not disable capture as the normal response to a recovery outage: leave it recording durable
events and pause processing instead. Outbox storage must be monitored.

## Processor configuration and legitimate verification

Configure secrets in the deployment environment, never in committed source:

```text
REPLICATION_ENABLED=false
REPLICATION_TOKEN=<independent random 256-bit secret; secrets.token_urlsafe(32) gives 43 characters>
REPLICATION_BATCH_SIZE=200
REPLICATION_TIME_BUDGET=15
REPLICATION_MAX_ATTEMPTS=8
```

Preserve the existing SSL options and add `connect_timeout=3` to both configured database URLs
before activation. Validate actual Render worker timeouts above the processing budget plus
connection/commit margin. No URL, secret, role or hosted setting was changed by this work.

After approved capture and clean reconciliation, **you** set `REPLICATION_ENABLED=true` and
redeploy/restart under the fence. Permit one controlled, legitimate source operation, such as a
normal user-created ticket. Do not run synthetic destructive cases against production.

Read-only verification in the corresponding database consoles, using the actual new ticket ID:

```sql
-- Singapore: original business key and captured event headers (no row payload).
SELECT id FROM public.api_ticket WHERE id = NEW_TICKET_ID;
SELECT event_uuid, transaction_id, event_type, status, attempts, applied_at
FROM public.replication_replicationevent
WHERE model_name='api_ticket'
  AND primary_key=jsonb_build_object('id', NEW_TICKET_ID)
ORDER BY id;
```

Invoke the protected processor yourself; this **does write replicated business rows to Sydney**:

```sh
curl --fail-with-body -X POST "$API_BASE_URL/api/replication/process/" -H "Authorization: Bearer $REPLICATION_TOKEN" -H 'Content-Type: application/json' -d '{}'
```

Then verify read-only:

```sql
-- Sydney: same PK; a receipt for the captured event UUID.
SELECT id FROM public.api_ticket WHERE id = NEW_TICKET_ID;
SELECT event_id, applied_at FROM public.replication_appliedreplicationevent
WHERE event_id = 'CAPTURED_EVENT_UUID';
```

Singapore's event must now be `APPLIED` with `applied_at` populated. Other events in the same
source transaction must have target receipts and source acknowledgements too. The processor
applies a source transaction atomically, never skips a blocked head and never splits it for a batch.

```sh
curl --fail-with-body "$API_BASE_URL/api/replication/status/" -H "Authorization: Bearer $REPLICATION_TOKEN"
python manage.py replication_inspect --events
```

The curl snippets use Bash environment syntax. PowerShell equivalent, after the owner has set
the same token securely in the environment (never put its literal value into a saved script):

```powershell
$ilabApiBase = "https://YOUR_RENDER_HOST"
$ilabReplicationHeaders = @{ Authorization = "Bearer " + $env:REPLICATION_TOKEN }
Invoke-RestMethod -Method Post -Uri "$ilabApiBase/api/replication/process/" -Headers $ilabReplicationHeaders -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Method Get -Uri "$ilabApiBase/api/replication/status/" -Headers $ilabReplicationHeaders
```

Monitor separate connectivity booleans, metrics availability, `schema_compatible`, `capture_ready`,
`processor_running`, counts, oldest age and `last_run_error_code`. Unavailable checks are unknown,
not proof of divergence. `applied` counts acknowledged source events, including safe redeliveries;
it is not a count of newly changed target rows. An empty queue never proves equality.

Rollback: disable processing and drain in-flight requests; preserve capture, events and receipts.
A target commit with a lost source acknowledgement is repaired by redelivery, not record deletion.
Do not reverse legitimate business writes as a routine infrastructure rollback.

## QStash — owner setup only

No schedule, provider API call, persistent access key or QStash setting was created/modified.

| Field | Value |
| --- | --- |
| Destination | `https://YOUR_RENDER_HOST/api/replication/process/` (exact HTTPS URL, trailing slash) |
| Method | POST |
| Body | `{}` |
| Content-Type | `application/json` |
| Cron | `*/5 * * * *` |
| Forwarded destination Authorization | `Bearer <REPLICATION_TOKEN>` |
| Retries | 2 |
| Delivery timeout | Start with 90 seconds; validate plan and measured cold starts |
| Callbacks | None required |

In QStash's API form, forwarding uses `Upstash-Forward-Authorization`. QStash API authentication
uses its **separate** API token. In the console, enter the destination's Authorization header in the
forwarded-header settings; verify the delivered request contains it. Do not substitute a business
JWT or `SCHEDULER_TOKEN`. Avoid logging request headers in Render/QStash/debugging tools.

The periodic interval is five minutes regardless of UTC/Manila timezone. Expect 288 normal
deliveries/day, plus retry attempts and any other schedules. Check account quota/current usage
yourself. Disable/pause the schedule if rolling back; keep the outbox intact.

References: [QStash schedule API](https://upstash.com/docs/qstash/api-reference/schedules/create-a-schedule),
[QStash limits](https://upstash.com/pricing/qstash), [Render cold starts](https://render.com/docs/free).

## Limits, failures and recovery

Receipt reads/inserts are batched per transaction. Adjacent same-table INSERTs use one strict bulk
statement; UPDATE/DELETE combine PK lookup and before-image checking in their atomic DML. They
are not reordered or grouped across intervening events. Target DML still requires network round
trips; this is not a production throughput benchmark. Global capture locking serializes
approved source write transactions and can add latency/deadlocks around other application locks.
Test realistic imports, transfers and multi-row operations on disposable copies before approval.

The HTTP budget is cooperative, not a hard guarantee for DNS stalls or slow COMMIT. Work is
bounded by event count and deadlines. A source transaction larger than the configured batch
blocks with `TRANSACTION_TOO_LARGE`; a slow transaction rolls back as a unit and retries, eventually
requiring operator attention. Do not split transactions, skip events or raise HTTP budgets beyond
the hosting timeout to hide this. Rehearse the largest legitimate transaction and revise a bounded
operator recovery plan if it cannot fit. No paid worker or uncontrolled background thread is used.
Each process request occupies a normal web worker. Review the deployed worker concurrency/memory
and application response latency before activation; existing Gunicorn configuration was not changed.

Sydney outage: leave Singapore capture on, investigate connectivity, and resume processing when
safe. Transient events use durable backoff; after retry exhaustion or a conflict, diagnose the head
before requeueing. A partial receipt set for one transaction is corruption and blocks replay.

```sh
# Read-only diagnostics.
python manage.py replication_inspect --events
# Owner-only bookkeeping write, after the cause is resolved; never skips payloads.
python manage.py replication_retry TRANSACTION_ID --conflict-resolved
```

Reconciliation is read-only but temporarily blocks captured writers with the source advisory lock;
run it in a suitable quiet/maintenance window after draining the queue. Divergence is never
automatically overwritten. No automatic purge exists: outbox growth and storage quotas need
monitoring and an explicitly approved retention policy. Historical error text is redacted from
operator event diagnostics to avoid exposing old exception details.

Manual failover: fence Singapore at the provider/role/network level, stop all app/scheduler writes
and processing, inspect the available recovery point and explicitly accept any unknown/unapplied
loss. Snapshot and verify Sydney, then reseed **all** sequence-backed IDs without lowering current
allocations. Only then may you approve and manually change routing/grants to one writable primary.
Sydney's audit sequence was already behind copied IDs during preflight; explicit-ID replay does
not advance any target business sequence. Never promote automatically or allow dual writes.

When Singapore returns, keep it fenced; do not blindly replay the old forward queue into a promoted
Sydney. Snapshot both, reconcile source-only operations under a reviewed plan and establish a new
verified baseline/direction. Failback is another separately approved maintenance operation. See
README's full manual DR runbook. A five-minute schedule is not a guaranteed five-minute RPO.
