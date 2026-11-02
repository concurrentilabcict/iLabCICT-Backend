"""Read-only catalog inspection. Fail closed when physical schemas differ."""
import time
import re
from pathlib import Path
from django.db import connections, transaction
from django.db.backends.postgresql.psycopg_any import sql

from .registry import TABLES, TRIGGERS, INFRA_TABLES


class ReplicationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class DeadlineCursor:
    def __init__(self, cursor, deadline):
        self.cursor, self.deadline = cursor, deadline

    def execute(self, query, params=None):
        if self.deadline is not None:
            remaining = int((self.deadline - time.monotonic()) * 1000)
            if remaining < 100:
                raise ReplicationError("TIME_BUDGET")
            self.cursor.execute("SET LOCAL statement_timeout = %s", [remaining])
        self.cursor.execute(query, params)

    def fetchall(self):
        return self.cursor.fetchall()


def catalog(alias, deadline=None):
    inspected_tables = list(TABLES + INFRA_TABLES)
    with connections[alias].cursor() as raw_cursor:
        c = DeadlineCursor(raw_cursor, deadline)
        c.execute("""SELECT t.relname, a.attname, format_type(a.atttypid,a.atttypmod),
                   a.attnotnull, a.attidentity, a.attgenerated,
                   pg_get_expr(d.adbin,d.adrelid), a.attnum
            FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_attribute a ON a.attrelid=t.oid
            LEFT JOIN pg_attrdef d ON d.adrelid=t.oid AND d.adnum=a.attnum
            WHERE n.nspname='public' AND t.relname = ANY(%s)
              AND a.attnum>0 AND NOT a.attisdropped ORDER BY t.relname,a.attnum""", [inspected_tables])
        columns = c.fetchall()
        c.execute("""SELECT t.relname, con.contype, pg_get_constraintdef(con.oid), con.condeferrable, con.condeferred,
                   COALESCE((to_jsonb(con)->>'conenforced')::boolean,true), con.convalidated
            FROM pg_constraint con JOIN pg_class t ON t.oid=con.conrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relname=ANY(%s) ORDER BY 1,2,3""", [inspected_tables])
        constraints = c.fetchall()
        c.execute("""SELECT tablename,indexdef FROM pg_indexes WHERE schemaname='public'
            AND tablename=ANY(%s) ORDER BY 1,2""", [inspected_tables])
        indexes = c.fetchall()
        c.execute("SELECT app,name FROM public.django_migrations ORDER BY app,name")
        migrations = c.fetchall()
        c.execute("""SELECT t.relname,tr.tgname,tr.tgenabled,pg_get_triggerdef(tr.oid)
            FROM pg_trigger tr JOIN pg_class t ON t.oid=tr.tgrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE NOT tr.tgisinternal AND n.nspname='public' ORDER BY 1,2""")
        triggers = c.fetchall()
        c.execute("""SELECT t.relname,tr.tgname,tr.tgtype,p.proname,nf.nspname,p.prosrc,p.proconfig,p.prosecdef
            FROM pg_trigger tr JOIN pg_class t ON t.oid=tr.tgrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace JOIN pg_proc p ON p.oid=tr.tgfoid
            JOIN pg_namespace nf ON nf.oid=p.pronamespace
            WHERE NOT tr.tgisinternal AND n.nspname='public' ORDER BY 1,2""")
        trigger_details = c.fetchall()
        c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [r[0] for r in c.fetchall()]
        c.execute("""SELECT t.relname FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relname=ANY(%s)
              AND (t.relrowsecurity OR t.relkind <> 'r')""", [inspected_tables])
        unsupported = c.fetchall()
        c.execute("""SELECT t.relname,a.attname FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, position)
                ON k.position <= i.indnkeyatts
            JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum
            WHERE n.nspname='public' AND t.relname=ANY(%s) AND i.indisprimary
            ORDER BY t.relname,k.position""", [inspected_tables])
        keys = {}
        for table, column in c.fetchall():
            keys.setdefault(table, []).append(column)
        c.execute("""SELECT s.seqcache,s.seqincrement,s.seqcycle FROM pg_sequence s
            WHERE s.seqrelid=pg_get_serial_sequence('public.replication_replicationevent','id')::regclass""")
        outbox_sequence = c.fetchall()
    return dict(columns=columns, constraints=constraints, indexes=indexes, migrations=migrations,
                triggers=triggers, trigger_details=trigger_details, tables=tables, unsupported=unsupported,
                keys=keys, outbox_sequence=outbox_sequence)


def schema_signature(info):
    """Compare replay semantics across restored column orders and PostgreSQL 17/18.

    Replay names every column explicitly; physical attribute positions do not
    change its meaning. PostgreSQL 18 adds NOT NULL constraint catalog rows;
    nullability is already compared for every column through attnotnull.
    """
    return {
        "columns": sorted(row[:-1] for row in info["columns"]),
        "constraints": sorted(row for row in info["constraints"] if row[1] != "n"),
        **{key: info[key] for key in ("indexes", "migrations", "keys")},
    }


def compatible(require_capture=True, deadline=None):
    source, target = catalog("default", deadline), catalog("recovery", deadline)
    if source["outbox_sequence"] != [(1, 1, False)]:
        raise ReplicationError("UNSAFE_OUTBOX_SEQUENCE")
    source_signature, target_signature = schema_signature(source), schema_signature(target)
    for field in source_signature:
        if source_signature[field] != target_signature[field]:
            raise ReplicationError("SCHEMA_MISMATCH")
    for info in (source, target):
        if any(not row[5] or not row[6] for row in info["constraints"]):
            raise ReplicationError("UNENFORCED_OR_UNVALIDATED_CONSTRAINT")
        if info["unsupported"] or set(info["keys"]) != set(TABLES + INFRA_TABLES):
            raise ReplicationError("UNSUPPORTED_SCHEMA")
        extras = set(info["tables"]) - set(TABLES) - {"django_migrations"}
        if extras - set(INFRA_TABLES):
            raise ReplicationError("UNREVIEWED_TABLE")
        if any(t[5] for t in info["columns"]):
            raise ReplicationError("GENERATED_COLUMN_UNSUPPORTED")
    if target["triggers"]:
        raise ReplicationError("RECOVERY_TRIGGERS_PRESENT")
    frozen = Path(__file__).with_name("migrations").joinpath("capture_v1.sql").read_text()
    bodies = {name: body.strip() for name, body in re.findall(r"FUNCTION public\.(\w+)\(\).*?AS \$\$(.*?)\$\$;", frozen, re.S)}
    specifications = {"ilab_order": (30, "order"), "ilab_capture": (29, "capture"), "ilab_no_truncate": (34, "no_truncate")}
    for table, name, kind, function, namespace, body, config, security_definer in source["trigger_details"]:
        if name not in specifications:
            raise ReplicationError("UNREVIEWED_TRIGGER")
        expected_kind, suffix = specifications[name]
        expected_function = "ilab_replication_" + suffix
        expected_config = {"search_path=pg_catalog, public"} if suffix in {"order", "capture"} else set()
        if suffix == "capture":
            expected_config.add("TimeZone=UTC")
        if (table not in TABLES or kind != expected_kind or function != expected_function
                or namespace != "public" or body.strip() != bodies[expected_function] or security_definer
                or set(config or []) != expected_config):
            raise ReplicationError("CAPTURE_DEFINITION_MISMATCH")
    if require_capture:
        expected = {(t, n) for t in TABLES for n in TRIGGERS}
        actual = {(t, n) for t, n, enabled, _ in source["triggers"] if enabled == "O"}
        if actual != expected or len(source["triggers"]) != len(expected):
            raise ReplicationError("CAPTURE_NOT_READY")
    return source


def reconcile():
    """Stream sorted whole-row hashes; no row payload is returned. O(1) client memory.

    Source capture lock gives a stable cut; never writes either database.
    Queue must be empty; freeze external Sydney writers operationally.
    """
    from .models import ReplicationEvent
    from .registry import CAPTURE_LOCK
    import hashlib
    with transaction.atomic(using="default"), transaction.atomic(using="recovery"):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                level = "READ COMMITTED" if alias == "default" else "REPEATABLE READ"
                # Source reads become stable *after* acquiring the capture lock.
                # Taking a repeatable snapshot before waiting for it could miss
                # the writer whose commit released that lock.
                c.execute(f"SET TRANSACTION ISOLATION LEVEL {level}, READ ONLY")
                c.execute("SET LOCAL statement_timeout = '30s'")
                c.execute("SET LOCAL lock_timeout = '2s'")
                c.execute("SET LOCAL timezone = 'UTC'")
        with connections["default"].cursor() as c:
            c.execute("SELECT pg_advisory_xact_lock(%s)", [CAPTURE_LOCK])
        compatible()
        if ReplicationEvent.objects.using("default").exclude(status="APPLIED").exists():
            raise ReplicationError("QUEUE_NOT_DRAINED")
        result = {}
        for table in TABLES:
            values = []
            for alias in ("default", "recovery"):
                digest, count = hashlib.sha256(), 0
                query = sql.SQL("SELECT encode(sha256(convert_to(to_jsonb(t)::text, 'UTF8')), 'hex') FROM public.{} t ORDER BY 1").format(sql.Identifier(table))
                # Server-side cursor avoids loading complete tables into application memory.
                with connections[alias].chunked_cursor() as c:
                    c.execute(query)
                    while rows := c.fetchmany(1000):
                        for (row_hash,) in rows:
                            digest.update(row_hash.encode("ascii"))
                            count += 1
                values.append((count, digest.hexdigest()))
            result[table] = {"source_count": values[0][0], "recovery_count": values[1][0], "matches": values[0] == values[1]}
        return result
