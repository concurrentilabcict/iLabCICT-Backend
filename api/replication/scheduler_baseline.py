"""Narrow, operator-owned bootstrap repair. Not called by HTTP or normal replay.

Only the one-row scheduler baseline's two execution timestamps may be copied.
Dry-run is read-only. Apply is a separate, explicitly gated manual operation.
"""
import hashlib
import json
import secrets

from django.conf import settings
from django.db import connections, transaction

from .registry import TABLES, TRIGGERS, PROCESS_LOCK, INFRA_TABLES
from .schema import ReplicationError, catalog, schema_signature

FIELDS = {"last_execution", "next_execution"}


def _bootstrap_safe():
    source, target = catalog("default"), catalog("recovery")
    if schema_signature(source) != schema_signature(target):
        raise ReplicationError("SCHEMA_MISMATCH")
    for info in (source, target):
        if not set(TABLES).issubset(info["tables"]) or info["unsupported"]:
            raise ReplicationError("UNSUPPORTED_SCHEMA")
        if set(info["tables"]) - set(TABLES) - set(INFRA_TABLES) - {"django_migrations"}:
            raise ReplicationError("UNREVIEWED_TABLE")
        if any(not row[5] or not row[6] for row in info["constraints"]):
            raise ReplicationError("UNENFORCED_OR_UNVALIDATED_CONSTRAINT")
        if info["keys"].get("api_taskscheduler") != ["id"]:
            raise ReplicationError("SCHEDULER_KEY_CHANGED")
    allowed = {(table, name) for table in TABLES for name in TRIGGERS}
    if target["triggers"] or any((table, name) not in allowed or enabled != "D"
                                 for table, name, enabled, _ in source["triggers"]):
        raise ReplicationError("BOOTSTRAP_REQUIRES_CAPTURE_OFF")
    for alias in ("default", "recovery"):
        with connections[alias].cursor() as c:
            c.execute("SELECT EXISTS(SELECT 1 FROM public.replication_replicationevent), EXISTS(SELECT 1 FROM public.replication_appliedreplicationevent)")
            if any(c.fetchone()):
                raise ReplicationError("BOOTSTRAP_REQUIRES_EMPTY_HISTORY")


def _row(alias):
    with connections[alias].cursor() as c:
        c.execute("SELECT to_jsonb(t)::text FROM public.api_taskscheduler t ORDER BY id LIMIT 2")
        rows = c.fetchall()
    if len(rows) != 1:
        raise ReplicationError("SCHEDULER_REPAIR_REQUIRES_SINGLE_ROW")
    raw = rows[0][0]
    return raw, json.loads(raw), hashlib.sha256(raw.encode("utf-8")).hexdigest()


def reconcile_scheduler(*, apply=False, expected_source=None, expected_target=None,
                        maintenance_window=False, backup_confirmed=False):
    if getattr(settings, "REPLICATION_ENABLED", False):
        raise ReplicationError("DISABLE_PROCESSING_FIRST")
    if apply and (not maintenance_window or not backup_confirmed
                  or not expected_source or not expected_target):
        raise ReplicationError("EXPLICIT_REPAIR_APPROVAL_REQUIRED")
    # Recovery commits before the source lock is released. No source DML occurs.
    with transaction.atomic(using="default"), transaction.atomic(using="recovery"):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                if not apply:
                    c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                c.execute("SET LOCAL timezone='UTC'")
                c.execute("SET LOCAL statement_timeout='15s'")
                c.execute("SET LOCAL lock_timeout='2s'")
        if apply:
            with connections["default"].cursor() as c:
                c.execute("SELECT pg_try_advisory_xact_lock(%s)", [PROCESS_LOCK])
                if not c.fetchone()[0]:
                    raise ReplicationError("PROCESSOR_BUSY")
                # Lock before reading the fingerprint so a concurrent scheduler
                # cannot change the authoritative timestamps during this copy.
                c.execute("LOCK TABLE public.api_taskscheduler IN SHARE MODE")
            with connections["recovery"].cursor() as c:
                c.execute("LOCK TABLE public.api_taskscheduler IN SHARE ROW EXCLUSIVE MODE")
        _bootstrap_safe()
        source_raw, source, source_hash = _row("default")
        target_raw, target, target_hash = _row("recovery")
        if set(source) != set(target) or source["id"] != target["id"]:
            raise ReplicationError("SCHEDULER_ROW_IDENTITY_CONFLICT")
        differences = sorted(key for key in source if source[key] != target[key])
        if set(differences) - FIELDS:
            raise ReplicationError("SCHEDULER_NON_TIMESTAMP_CONFLICT")
        result = {"mode": "APPLY" if apply else "READ_ONLY", "table": "api_taskscheduler",
                  "changed_columns": differences, "source_fingerprint": source_hash,
                  "target_fingerprint": target_hash, "rows_updated": 0,
                  "authoritative_database": "default", "global_write_fence_verified": False}
        if not apply:
            return result
        if (not secrets.compare_digest(source_hash, expected_source)
                or not secrets.compare_digest(target_hash, expected_target)):
            raise ReplicationError("SCHEDULER_PLAN_STALE")
        if differences:
            with connections["recovery"].cursor() as c:
                c.execute("""UPDATE public.api_taskscheduler t
                    SET last_execution=s.last_execution, next_execution=s.next_execution
                    FROM jsonb_populate_record(NULL::public.api_taskscheduler,%s::jsonb) s
                    WHERE t.id=s.id AND to_jsonb(t)=%s::jsonb""", [source_raw, target_raw])
                if c.rowcount != 1:
                    raise ReplicationError("SCHEDULER_COMPARE_AND_SWAP_FAILED")
            # Verify while the recovery transaction can still roll back.
            _, _, updated_hash = _row("recovery")
            if updated_hash != source_hash:
                raise ReplicationError("SCHEDULER_REPAIR_VERIFICATION_FAILED")
            result["rows_updated"] = 1
        return result
