"""Ordered transactional outbox replay. No business model save methods or signals."""
import hashlib
import json
import time
from datetime import timedelta
from contextlib import contextmanager

from django.conf import settings
from django.db import DatabaseError, connections, transaction
from django.db.models import Count, Min, Max
from django.db.models import TextField
from django.db.models.functions import Cast
from django.utils import timezone
from django.db.backends.postgresql.psycopg_any import sql

from .models import AppliedReplicationEvent, ReplicationEvent, ReplicationRun
from .registry import PROCESS_LOCK, TABLES, TRIGGERS
from .schema import ReplicationError, compatible


def validate_event(event, schema):
    table = event.model_name
    if table not in TABLES or event.event_type not in {"INSERT", "UPDATE", "DELETE"}:
        raise ReplicationError("INVALID_EVENT")
    columns = [r[1] for r in schema["columns"] if r[0] == table]
    keys = schema["keys"][table]
    if (not event.transaction_id or not isinstance(event.primary_key, dict)
            or set(event.primary_key) != set(keys)
            or any(v is None for v in event.primary_key.values())):
        raise ReplicationError("INVALID_PRIMARY_KEY")
    for row, required in ((event.old_row, event.event_type != "INSERT"),
                          (event.payload, event.event_type != "DELETE")):
        if required:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ReplicationError("INVALID_ROW_SHAPE")
        elif row is not None:
            raise ReplicationError("INVALID_ROW_SHAPE")
    before = event.old_row if event.old_row is not None else event.payload
    if any(before[k] != event.primary_key[k] for k in keys):
        raise ReplicationError("INVALID_PRIMARY_KEY")
    return columns, keys


def event_digest(event):
    fields = [str(event.event_uuid), event.transaction_id, event.model_name,
              event.event_type, event._key_json, event._old_json, event._payload_json]
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _insert_events(events, schema, cursor):
    columns, _ = validate_event(events[0], schema)
    for event in events:
        if event.event_type != "INSERT" or event.model_name != events[0].model_name:
            raise ReplicationError("INVALID_EVENT")
        validate_event(event, schema)
    table = sql.SQL("public.{}").format(sql.Identifier(events[0].model_name))
    names = sql.SQL(", ").join(map(sql.Identifier, columns))
    selected = sql.SQL(", ").join(sql.SQL("r.{}").format(sql.Identifier(c)) for c in columns)
    # Preserve native JSON precision. Strict INSERT never upserts or overwrites
    # pre-existing Sydney rows; any unique conflict rolls back the whole group.
    rows = "[" + ",".join(event._payload_json for event in events) + "]"
    try:
        cursor.execute(sql.SQL("INSERT INTO {} ({}) OVERRIDING SYSTEM VALUE SELECT {} FROM jsonb_populate_recordset(NULL::{}, %s::jsonb) r").format(table, names, selected, table), [rows])
    except DatabaseError as exc:
        cause = exc.__cause__ or exc
        if (getattr(cause, "pgcode", None) or getattr(cause, "sqlstate", None)) == "23505":
            raise ReplicationError("INSERT_CONFLICT") from None
        raise
    if cursor.rowcount != len(events):
        raise ReplicationError("ROW_COUNT_CONFLICT")


def apply_event(event, schema, cursor):
    columns, keys = validate_event(event, schema)
    if event.event_type == "INSERT":
        return _insert_events([event], schema, cursor)
    table = sql.SQL("public.{}").format(sql.Identifier(event.model_name))
    # PKs are non-null. Equality supports index access. The before-image check
    # is part of the DML itself and is rechecked after waiting for a row lock;
    # no separate read/check/write race or extra lock-read round trip is needed.
    predicate = sql.SQL(" AND ").join(
        sql.SQL("t.{} = k.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys)
    predicate += sql.SQL(" AND to_jsonb(t) = %s::jsonb")
    if event.event_type == "DELETE":
        cursor.execute(sql.SQL("DELETE FROM {} t USING jsonb_populate_record(NULL::{}, %s::jsonb) k WHERE {}").format(table, table, predicate),
                       [event._key_json, event._old_json])
    else:
        assignments = sql.SQL(", ").join(sql.SQL("{} = r.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in columns)
        cursor.execute(sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{}, %s::jsonb) r, jsonb_populate_record(NULL::{}, %s::jsonb) k WHERE {}").format(table, assignments, table, table, predicate),
                       [event._payload_json, event._key_json, event._old_json])
    if cursor.rowcount != 1:
        raise ReplicationError("BEFORE_IMAGE_CONFLICT")


def classify_error(exc):
    if isinstance(exc, ReplicationError):
        return exc.code, exc.code == "TIME_BUDGET"
    cause = exc.__cause__ or exc
    code = getattr(cause, "pgcode", None) or getattr(cause, "sqlstate", None)
    transient = bool(code and (code[:2] in {"08", "40", "53"} or code in {"55P03", "57014", "57P01", "57P02", "57P03"}))
    if isinstance(exc, DatabaseError) and code is None:
        transient = True
    diagnostic = {"23503": "FOREIGN_KEY_CONFLICT", "23505": "UNIQUE_CONFLICT",
                  "23502": "NOT_NULL_CONFLICT", "23514": "CHECK_CONFLICT",
                  "42501": "DATABASE_PERMISSION"}.get(code, "DATABASE_CONFLICT")
    return ("TRANSIENT_DATABASE" if transient else diagnostic), transient


def _apply_group(events, schema, deadline):
    with transaction.atomic(using="recovery"):
        with connections["recovery"].cursor() as c:
            c.execute("SET LOCAL timezone = 'UTC'")
            c.execute("SET LOCAL lock_timeout = '1s'")
            c.execute("SET LOCAL statement_timeout = %s", [max(100, int((deadline-time.monotonic())*1000))])
            c.execute("SELECT pg_advisory_xact_lock(%s)", [PROCESS_LOCK])
            if time.monotonic() >= deadline - 0.1:
                raise ReplicationError("TIME_BUDGET")
            receipts = dict(AppliedReplicationEvent.objects.using("recovery").filter(
                event_id__in=[event.event_uuid for event in events]).values_list("event_id", "digest"))
            if receipts:
                if len(receipts) != len(events):
                    raise ReplicationError("PARTIAL_TRANSACTION_RECEIPTS")
                for event in events:
                    validate_event(event, schema)
                    if receipts[event.event_uuid] != event_digest(event):
                        raise ReplicationError("RECEIPT_MISMATCH")
                return
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            position = 0
            while position < len(events):
                event = events[position]
                remaining = int((deadline - time.monotonic()) * 1000)
                if remaining < 100:
                    raise ReplicationError("TIME_BUDGET")
                c.execute("SET LOCAL statement_timeout = %s", [remaining])
                end = position+1
                if event.event_type == "INSERT":
                    while (end < len(events) and events[end].event_type == "INSERT"
                           and events[end].model_name == event.model_name):
                        end += 1
                    _insert_events(events[position:end], schema, c)
                else:
                    apply_event(event, schema, c)
                position = end
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining < 100:
                raise ReplicationError("TIME_BUDGET")
            c.execute("SET LOCAL statement_timeout = %s", [remaining])
            AppliedReplicationEvent.objects.using("recovery").bulk_create([
                AppliedReplicationEvent(event_id=event.event_uuid, digest=event_digest(event)) for event in events])
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")


def process_pending_events(limit=None):
    if not getattr(settings, "REPLICATION_ENABLED", False):
        return {"outcome": "DISABLED", "applied": 0}
    limit = max(1, min(limit or settings.REPLICATION_BATCH_SIZE, settings.REPLICATION_BATCH_SIZE))
    budget = settings.REPLICATION_TIME_BUDGET
    started = time.monotonic()
    deadline = started + budget
    result = {"outcome": "OK", "applied": 0, "failed": 0, "transactions": 0}
    # Source transaction contains only replication bookkeeping; Neon's pooler can
    # keep the transaction lock until acknowledgement commits or rolls back.
    with transaction.atomic(using="default"):
        with connections["default"].cursor() as c:
            c.execute("SET LOCAL statement_timeout = %s", [int(budget * 1000)])
            c.execute("SET LOCAL lock_timeout = '1s'")
            c.execute("SELECT pg_try_advisory_xact_lock(%s)", [PROCESS_LOCK])
            if not c.fetchone()[0]:
                return {"outcome": "BUSY", "applied": 0}
        run = ReplicationRun.objects.using("default").create()
        try:
            with transaction.atomic(using="recovery"):
                with connections["recovery"].cursor() as c:
                    c.execute("SET LOCAL statement_timeout = %s", [max(100, int((deadline-time.monotonic())*1000))])
                schema = compatible(deadline=deadline)
            while result["applied"] < limit and time.monotonic() < deadline - 0.5:
                head = ReplicationEvent.objects.using("default").exclude(status="APPLIED").order_by("id").first()
                if head is None:
                    break
                if head.status == "FAILED":
                    raise ReplicationError("FAILED_HEAD")
                if head.next_retry_at and head.next_retry_at > timezone.now():
                    result["outcome"] = "RETRY_WAIT"
                    break
                group = list(ReplicationEvent.objects.using("default").filter(transaction_id=head.transaction_id).annotate(
                    _payload_json=Cast("payload", TextField()), _old_json=Cast("old_row", TextField()),
                    _key_json=Cast("primary_key", TextField())).order_by("id")[:limit + 1])
                if len(group) > limit:
                    raise ReplicationError("TRANSACTION_TOO_LARGE")
                if len(group) + result["applied"] > limit:
                    break
                try:
                    _apply_group(group, schema, deadline)
                except Exception as exc:
                    code, transient = classify_error(exc)
                    if code == "TIME_BUDGET":
                        transient = True
                    attempts = head.attempts + 1
                    retry = transient and attempts < settings.REPLICATION_MAX_ATTEMPTS
                    ReplicationEvent.objects.using("default").filter(pk__in=[e.pk for e in group]).update(
                        attempts=attempts, status="PENDING" if retry else "FAILED", last_error=code,
                        next_retry_at=timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** min(attempts, 7))) if retry else None)
                    result.update(outcome="RETRY" if retry else "BLOCKED", error_code=code, failed=len(group))
                    break
                ReplicationEvent.objects.using("default").filter(pk__in=[e.pk for e in group]).update(
                    status="APPLIED", applied_at=timezone.now(), attempts=head.attempts+1, last_error=None, next_retry_at=None)
                result["applied"] += len(group)
                result["transactions"] += 1
        except Exception as exc:
            code, transient = classify_error(exc)
            result.update(outcome="UNAVAILABLE" if transient else "BLOCKED", error_code=code)
        run.finished_at = timezone.now()
        run.duration_seconds = time.monotonic() - started
        run.applied = result["applied"]
        run.outcome = result["outcome"]
        run.error_code = result.get("error_code", "")
        run.save(using="default")
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result


@contextmanager
def _status_cursor(alias, timeout_ms=3000):
    with transaction.atomic(using=alias), connections[alias].cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("SET LOCAL statement_timeout = %s", [timeout_ms])
        yield cursor


def replication_status():
    metrics = {"enabled": getattr(settings, "REPLICATION_ENABLED", False), "singapore_connected": False,
               "sydney_connected": False, "schema_compatible": None, "capture_ready": None,
               "consistency_verified": False, "metrics_available": False, "metrics_error_code": None,
               "processor_running": None, "pending_events": None, "failed_events": None,
               "oldest_pending_age_seconds": None, "replication_lag_seconds": None,
               "last_successful_replication": None, "processing_duration_seconds": None,
               "last_run_outcome": None, "last_run_error_code": None, "schema_error_code": None}
    for alias, key in (("default", "singapore_connected"), ("recovery", "sydney_connected")):
        try:
            with _status_cursor(alias) as cursor:
                cursor.execute("SELECT 1")
            metrics[key] = True
        except Exception:
            pass
    if metrics["singapore_connected"]:
        try:
            with _status_cursor("default"):
                events = ReplicationEvent.objects.using("default")
                counts = dict(events.values("status").annotate(n=Count("id")).values_list("status", "n"))
                oldest = events.exclude(status="APPLIED").aggregate(t=Min("created_at"))["t"]
                last = events.aggregate(t=Max("applied_at"))["t"]
                run = ReplicationRun.objects.using("default").order_by("-id").first()
                age = max(0, (timezone.now()-oldest).total_seconds()) if oldest else None
                metrics.update(pending_events=counts.get("PENDING", 0), failed_events=counts.get("FAILED", 0),
                               oldest_pending_age_seconds=age, replication_lag_seconds=age,
                               last_successful_replication=last, processing_duration_seconds=run.duration_seconds if run else None,
                               last_run_outcome=run.outcome if run else None,
                               last_run_error_code=(run.error_code or None) if run else None, metrics_available=True)
        except Exception:
            # Missing infrastructure/metrics must not erase the successful ping.
            metrics["metrics_error_code"] = "METRICS_UNAVAILABLE"
        try:
            with _status_cursor("default", 1000) as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [PROCESS_LOCK])
                metrics["processor_running"] = not cursor.fetchone()[0]
                # Commit immediately releases the probe lock if it was free.
        except Exception:
            pass
    if metrics["singapore_connected"] and metrics["sydney_connected"]:
        try:
            with _status_cursor("default"), _status_cursor("recovery"):
                schema = compatible(require_capture=False, deadline=time.monotonic()+5)
            metrics["schema_compatible"] = True
            expected = {(table, name) for table in TABLES for name in TRIGGERS}
            actual = {(table, name) for table, name, enabled, _ in schema["triggers"] if enabled == "O"}
            metrics["capture_ready"] = actual == expected and len(schema["triggers"]) == len(expected)
        except Exception as exc:
            code = getattr(exc, "code", "SCHEMA_CHECK_UNAVAILABLE")
            metrics["schema_compatible"] = None if code in {"TIME_BUDGET", "SCHEMA_CHECK_UNAVAILABLE"} else False
            metrics["schema_error_code"] = code
    return metrics
