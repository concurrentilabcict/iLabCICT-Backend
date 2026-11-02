"""Stage B read-only diagnostics using only configured project credentials.

Run: python -m api.replication.preflight [--baseline]
No Django business startup, migrations, DML, secrets or row payload output.
"""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import time


def error_code(exc):
    cause = exc.__cause__ or exc
    state = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    if state:
        return state
    message = str(exc).lower()  # Classify internally; never emit the message.
    for snippets, code in (
        (("password authentication failed", "authentication failed"), "AUTHENTICATION_FAILED"),
        (("could not translate host", "getaddrinfo", "name or service not known", "no such host is known"), "DNS_RESOLUTION_FAILED"),
        (("unsupported startup parameter", "unsupported options", "unsupported startup option"), "STARTUP_OPTION_UNSUPPORTED"),
        (("timeout expired", "connection timeout", "timed out"), "CONNECTION_TIMEOUT"),
        (("forbidden by its access permissions", "permission denied"), "NETWORK_ACCESS_BLOCKED"),
        (("connection refused", "actively refused"), "CONNECTION_REFUSED"),
        (("ssl", "certificate", "tls"), "TLS_OR_SSL_FAILURE"),
    ):
        if any(snippet in message for snippet in snippets):
            return code
    return type(exc).__name__


def configure():
    from dotenv import load_dotenv
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env", override=False)
    if not all(os.environ.get(key) for key in ("DATABASE_URL", "RECOVERY_DATABASE_URL")):
        raise RuntimeError("CONFIGURED_DATABASE_CREDENTIALS_UNAVAILABLE")
    # Read the application's actual alias definitions, without its app startup/URLs.
    from ilabcict import settings as production
    from . import test_settings as isolated
    from django.conf import settings
    databases = copy.deepcopy(production.DATABASES)
    for config in databases.values():
        config["CONN_MAX_AGE"] = 0
        options = config.setdefault("OPTIONS", {})
        options["connect_timeout"] = 5
    settings.configure(
        SECRET_KEY="read-only-preflight-only", INSTALLED_APPS=isolated.INSTALLED_APPS,
        AUTH_USER_MODEL="api.User", DATABASES=databases, USE_TZ=True, TIME_ZONE="UTC",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField", REPLICATION_ENABLED=False,
        ROOT_URLCONF="api.replication.test_urls", MIDDLEWARE=[], REST_FRAMEWORK={"UNAUTHENTICATED_USER": None},
    )
    import django
    django.setup()
    return production


def baseline(column_catalogs=None):
    from django.db import connections, transaction
    from django.db.backends.postgresql.psycopg_any import sql
    from .registry import TABLES
    results = {}
    with transaction.atomic(using="default"), transaction.atomic(using="recovery"):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                c.execute("SET LOCAL timezone='UTC'")
                c.execute("SET LOCAL statement_timeout='30s'")
        # Force both snapshots before scanning; independent snapshots are not a write fence.
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("SELECT txid_current_snapshot()")
        for table in TABLES:
            checks = []
            for alias in ("default", "recovery"):
                count, digest = 0, hashlib.sha256()
                query = sql.SQL("SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') FROM public.{} t ORDER BY 1").format(sql.Identifier(table))
                with connections[alias].chunked_cursor() as c:
                    c.execute(query)
                    while rows := c.fetchmany(1000):
                        for (value,) in rows:
                            count += 1
                            digest.update(value.encode("ascii"))
                checks.append((count, digest.digest()))
            results[table] = {"source_count": checks[0][0], "target_count": checks[1][0], "matches": checks[0] == checks[1]}
            if checks[0] != checks[1] and column_catalogs:
                changed = []
                for column in (r[1] for r in column_catalogs["default"]["columns"] if r[0] == table):
                    digests = []
                    for alias in ("default", "recovery"):
                        digest = hashlib.sha256()
                        query = sql.SQL("SELECT encode(sha256(convert_to(COALESCE((to_jsonb(t)->%s)::text,'null'),'UTF8')),'hex') FROM public.{} t ORDER BY 1").format(sql.Identifier(table))
                        with connections[alias].chunked_cursor() as c:
                            c.execute(query, [column])
                            while rows := c.fetchmany(1000):
                                for (value,) in rows:
                                    digest.update(value.encode("ascii"))
                        digests.append(digest.digest())
                    if digests[0] != digests[1]:
                        changed.append(column)
                results[table]["differing_column_value_sets"] = changed
    return {"writer_fence_verified": False, "observation_only": True, "tables": results}


def inspect_alias(alias, production):
    from django.core.management import call_command
    from django.db import connections, transaction
    from django.db.migrations.executor import MigrationExecutor
    from .registry import TABLES, INFRA_TABLES
    from .schema import catalog
    config = connections[alias].settings_dict
    host = config.get("HOST") or ""
    region = "ap-southeast-1" if ".ap-southeast-1." in host else "ap-southeast-2" if ".ap-southeast-2." in host else "unverified"
    expected = "ap-southeast-1" if alias == "default" else "ap-southeast-2"
    result = {"configured": bool(config.get("HOST") and config.get("NAME")),
              "endpoint_fingerprint": hashlib.sha256((host + "/" + str(config.get("NAME"))).encode()).hexdigest()[:16],
              "configured_region": region, "expected_region_matches": region == expected,
              "original_connect_timeout_configured": bool(production.DATABASES[alias].get("OPTIONS", {}).get("connect_timeout"))}
    try:
        with transaction.atomic(using=alias), connections[alias].cursor() as c:
            # Neon poolers reject these as connection startup options. Set them
            # inside an explicit transaction, before any catalog/data query.
            c.execute("SET TRANSACTION READ ONLY")
            c.execute("SET LOCAL statement_timeout = '15s'")
            c.execute("SET LOCAL lock_timeout = '1s'")
            c.execute("SHOW transaction_read_only")
            if c.fetchone()[0] != "on":
                raise RuntimeError("READ_ONLY_GUARD_MISSING")
            c.execute("SELECT current_database(), current_setting('server_version_num'), pg_is_in_recovery()")
            database, version, physical_recovery = c.fetchone()
            result.update(connected=True, database_name_matches=database == config["NAME"],
                          postgres_version_num=version, physical_standby=physical_recovery, transaction_read_only=True)
            info = catalog(alias)
            result.update(tables=info["tables"], missing_approved_tables=sorted(set(TABLES)-set(info["tables"])),
                          unexpected_tables=sorted(set(info["tables"])-set(TABLES)-set(INFRA_TABLES)-{"django_migrations"}),
                          migration_leaves={}, replication_migrations=[name for app, name in info["migrations"] if app == "replication"],
                          primary_keys=info["keys"], constraints=info["constraints"],
                          trigger_headers=[row[:3] for row in info["triggers"]], outbox_sequence=info["outbox_sequence"],
                          unsupported_schema=info["unsupported"])
            c.execute("SELECT count(*) FILTER (WHERE status='PENDING'),count(*) FILTER (WHERE status='FAILED'), count(*) FILTER (WHERE status='APPLIED'), min(created_at) FILTER (WHERE status<>'APPLIED'), max(applied_at) FROM public.replication_replicationevent")
            pending, failed, applied, oldest, last = c.fetchone()
            result["outbox"] = dict(pending=pending, failed=failed, applied=applied, oldest_outstanding_at=oldest, last_acknowledgement_at=last)
            columns = {r[1] for r in info["columns"] if r[0] == "replication_replicationevent"}
            if "transaction_id" in columns:
                c.execute("SELECT count(*) FROM public.replication_replicationevent WHERE transaction_id='' OR event_type NOT IN ('INSERT','UPDATE','DELETE')")
            else:
                c.execute("SELECT count(*) FROM public.replication_replicationevent")
            result["legacy_event_count"] = c.fetchone()[0]
            c.execute("SELECT count(*) FROM public.replication_appliedreplicationevent")
            result["receipt_count"] = c.fetchone()[0]
            c.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND xact_start IS NOT NULL")
            result["other_active_transactions"] = c.fetchone()[0]
            c.execute("SELECT has_table_privilege(current_user,'public.api_room','INSERT,UPDATE,DELETE')")
            result["configured_role_has_business_write_privileges"] = c.fetchone()[0]
            executor = MigrationExecutor(connections[alias])
            executor.loader.check_consistent_history(connections[alias])
            leaves = executor.loader.graph.leaf_nodes()
            result["migration_leaves"] = dict(leaves)
            plan = executor.migration_plan([("replication", "0003_capture_definitions")])
            result["migration_plan"] = [{"app": m.app_label, "name": m.name, "backwards": backwards,
                                          "operations": [op.describe() for op in m.operations]} for m, backwards in plan]
            preview = io.StringIO()
            call_command("migrate", "replication", "0003_capture_definitions", database=alias,
                         plan=True, skip_checks=True, stdout=preview)
            result["django_migrate_plan_preview"] = preview.getvalue().strip()
        return result, info
    except Exception as exc:
        result.update(inspection_error=error_code(exc))
        return result, None


def sequence_check(alias):
    """Compare sequence allocations with keys without calling nextval/setval."""
    from django.db import connections, transaction
    from django.db.backends.postgresql.psycopg_any import sql
    from .registry import TABLES
    with transaction.atomic(using=alias), connections[alias].cursor() as c:
        c.execute("SET TRANSACTION READ ONLY")
        c.execute("SET LOCAL statement_timeout='15s'")
        c.execute("""WITH key_columns AS MATERIALIZED (
                SELECT t.relname,a.attname FROM pg_class t
                JOIN pg_namespace n ON n.oid=t.relnamespace
                JOIN pg_index i ON i.indrelid=t.oid AND i.indisprimary
                JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, position)
                    ON k.position <= i.indnkeyatts
                JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum
                WHERE n.nspname='public' AND t.relname=ANY(%s)
                    AND a.attnum>0 AND NOT a.attisdropped)
            SELECT k.relname,k.attname,ns.nspname,s.relname,ps.cache_size,ps.increment_by,ps.cycle
            FROM key_columns k
            JOIN pg_class s ON s.oid=pg_get_serial_sequence(format('%%I.%%I','public',k.relname),k.attname)::regclass
            JOIN pg_namespace ns ON ns.oid=s.relnamespace
            JOIN pg_sequences ps ON ps.schemaname=ns.nspname AND ps.sequencename=s.relname
            ORDER BY k.relname""", [list(TABLES)])
        sequences = c.fetchall()
        parts, parameters = [], []
        for table, column, schema, sequence, cache, increment, cycle in sequences:
            parts.append(sql.SQL("SELECT %s, s.last_value, s.is_called, (SELECT max({}) FROM public.{}) FROM {}.{} s").format(
                sql.Identifier(column), sql.Identifier(table), sql.Identifier(schema), sql.Identifier(sequence)))
            parameters.append(table)
        if not parts:
            return []
        c.execute(sql.SQL(" UNION ALL ").join(parts), parameters)
        positions = {table: (last, called, maximum) for table, last, called, maximum in c.fetchall()}
        results = []
        for table, column, schema, sequence, cache, increment, cycle in sequences:
            last, called, maximum = positions[table]
            next_candidate = last + increment if called else last
            results.append({"table": table, "column": column, "cache": cache, "increment": increment, "cycle": cycle,
                            "promotion_reseed_required": maximum is not None and next_candidate <= maximum,
                            "cached_values_require_operator_review": cache != 1 or increment != 1 or cycle})
        return results


def run(include_baseline=False):
    started = time.monotonic()
    production = configure()
    from django.core.management import call_command
    from django.db import connections, transaction
    from .schema import compatible, schema_signature
    report = {"mode": "READ_ONLY", "production_changes_performed": False,
              "local_replication_enabled": production.REPLICATION_ENABLED,
              "local_replication_token_configured": len(production.REPLICATION_TOKEN) >= 43,
              "databases": {}}
    try:
        infos = {}
        for alias in ("default", "recovery"):
            report["databases"][alias], infos[alias] = inspect_alias(alias, production)
        if all(infos.values()):
            report["distinct_configured_endpoints"] = report["databases"]["default"]["endpoint_fingerprint"] != report["databases"]["recovery"]["endpoint_fingerprint"]
            signatures = {alias: schema_signature(info) for alias, info in infos.items()}
            report["schema_sections_equal"] = {key: signatures["default"][key] == signatures["recovery"][key]
                                               for key in ("columns", "constraints", "indexes", "migrations", "keys")}
            column_maps = {alias: {(r[0], r[1]): r[2:] for r in info["columns"]} for alias, info in infos.items()}
            report["column_differences"] = [
                {"table": key[0], "column": key[1], "properties": [name for index, name in enumerate(
                    ("type", "not_null", "identity", "generated", "default", "position"))
                    if column_maps["default"].get(key, (None,)*6)[index] != column_maps["recovery"].get(key, (None,)*6)[index]]}
                for key in sorted(set(column_maps["default"]) | set(column_maps["recovery"]))
                if column_maps["default"].get(key) != column_maps["recovery"].get(key)]
            report["constraint_difference_kinds"] = {
                alias: sorted({r[1] for r in info["constraints"] if r not in infos["recovery" if alias == "default" else "default"]["constraints"]})
                for alias, info in infos.items()}
            output, errors = io.StringIO(), io.StringIO()
            try:
                call_command("replication_inspect", stdout=output, stderr=errors, skip_checks=True)
                report["replication_inspect"] = {"executed": True, "compatibility_code": errors.getvalue().strip() or "OK"}
            except Exception as exc:
                report["replication_inspect"] = {"executed": True, "error": error_code(exc)}
            try:
                with transaction.atomic(using="default"), transaction.atomic(using="recovery"):
                    for alias in ("default", "recovery"):
                        with connections[alias].cursor() as c:
                            c.execute("SET TRANSACTION READ ONLY")
                            c.execute("SET LOCAL statement_timeout = '15s'")
                    compatible(require_capture=False)
                report["activation_schema_ready"] = True
            except Exception as exc:
                report["activation_schema_ready"] = False
                report["activation_schema_code"] = getattr(exc, "code", error_code(exc))
            if include_baseline:
                try:
                    report["baseline"] = baseline(infos)
                except Exception as exc:
                    report["baseline"] = {"error": error_code(exc), "verified": False}
    finally:
        connections.close_all()
    report["duration_seconds"] = round(time.monotonic()-started, 3)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline", action="store_true")
    mode.add_argument("--sequences-only", action="store_true")
    mode.add_argument("--scheduler-plan", action="store_true", help="Read-only guarded scheduler repair plan; never applies it")
    parser.add_argument("--output", type=Path, help="Save sanitized metadata locally and print a compact summary")
    args = parser.parse_args()
    try:
        if args.scheduler_plan:
            configure()
            from .scheduler_baseline import reconcile_scheduler
            from django.db import connections
            try:
                report = {"mode": "READ_ONLY", "production_changes_performed": False,
                          "scheduler_plan": reconcile_scheduler(), "databases": {}}
            finally:
                connections.close_all()
        elif args.sequences_only:
            configure()
            from django.db import connections
            try:
                report = {"mode": "READ_ONLY", "production_changes_performed": False,
                          "databases": {alias: {"sequences": sequence_check(alias)} for alias in ("default", "recovery")}}
            finally:
                connections.close_all()
        else:
            report = run(args.baseline)
        if args.output:
            args.output.write_text(json.dumps(report, default=str, indent=2), encoding="utf-8")
            report = {key: value for key, value in report.items() if key != "databases"}
            report["databases"] = {alias: {key: value for key, value in data.items()
                                           if key not in {"constraints", "primary_keys", "tables"}}
                                    for alias, data in json.loads(args.output.read_text(encoding="utf-8"))["databases"].items()}
        print(json.dumps(report, default=str, indent=2))
    except Exception as exc:
        # Never print exception messages/tracebacks: driver errors can contain DSNs.
        print(json.dumps({"preflight_error": getattr(exc, "code", error_code(exc)), "production_changes_performed": False}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
