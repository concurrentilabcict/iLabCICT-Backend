from pathlib import Path
import re
from django.db import migrations

# Frozen allowlist: future additions require another reviewed migration.
TABLES = (
    "api_user", "api_room", "api_computer", "api_ticket", "api_repairlog",
    "api_maintenancehistory", "api_report", "api_requesthistory", "api_notification",
    "api_taskscheduler", "api_auditlogs", "api_userpushtoken", "api_otpcode",
    "api_printabletemplate", "api_user_groups", "api_user_user_permissions",
    "auth_group", "auth_permission", "auth_group_permissions", "django_content_type",
    "django_admin_log", "django_session",
)


def install(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return  # Sydney never receives capture functions or triggers.
    asset = Path(__file__).with_name("capture_v1.sql").read_text()
    bodies = {name: body.strip() for name, body in re.findall(r"FUNCTION public\.(\w+)\(\).*?AS \$\$(.*?)\$\$;", asset, re.S)}
    expected_types = {"ilab_order": 30, "ilab_capture": 29, "ilab_no_truncate": 34}
    # Never silently replace an unrelated definition or turn off active capture.
    # This check precedes every CREATE OR REPLACE / DROP in the frozen asset.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""SELECT t.relname,tr.tgname,tr.tgenabled,tr.tgtype,p.proname,nf.nspname
            FROM pg_trigger tr
            JOIN pg_class t ON t.oid=tr.tgrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_proc p ON p.oid=tr.tgfoid JOIN pg_namespace nf ON nf.oid=p.pronamespace
            WHERE n.nspname='public' AND t.relname=ANY(%s) AND NOT tr.tgisinternal""", [list(TABLES)])
        for table, name, enabled, kind, function, namespace in cursor.fetchall():
            if (name not in expected_types or kind != expected_types[name] or namespace != "public"
                    or function != "ilab_replication_" + name.removeprefix("ilab_")):
                raise RuntimeError("UNREVIEWED_EXISTING_TRIGGER")
            if enabled != "D":
                raise RuntimeError("CAPTURE_ALREADY_ACTIVE")
        cursor.execute("""SELECT p.proname,p.prosrc,p.proconfig,p.prosecdef FROM pg_proc p
            JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.proname=ANY(%s)""", [list(bodies)])
        for name, body, config, security_definer in cursor.fetchall():
            expected_config = set()
            if name != "ilab_replication_no_truncate":
                expected_config.add("search_path=pg_catalog, public")
            if name == "ilab_replication_capture":
                expected_config.add("TimeZone=UTC")
            if body.strip() != bodies[name] or set(config or []) != expected_config or security_definer:
                raise RuntimeError("EXISTING_CAPTURE_FUNCTION_MISMATCH")
    schema_editor.execute(asset, params=None)
    q = schema_editor.quote_name
    for table in TABLES:
        target = 'public.' + q(table)
        for name, timing, function in (
            ("ilab_order", "BEFORE INSERT OR UPDATE OR DELETE", "order"),
            ("ilab_capture", "AFTER INSERT OR UPDATE OR DELETE", "capture"),
            ("ilab_no_truncate", "BEFORE TRUNCATE", "no_truncate"),
        ):
            schema_editor.execute(f'DROP TRIGGER IF EXISTS {q(name)} ON {target}')
            granularity = "ROW" if name == "ilab_capture" else "STATEMENT"
            schema_editor.execute(f'CREATE TRIGGER {q(name)} {timing} ON {target} FOR EACH {granularity} EXECUTE FUNCTION public.ilab_replication_{function}()')
            schema_editor.execute(f'ALTER TABLE {target} DISABLE TRIGGER {q(name)}')


def uninstall(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return
    q = schema_editor.quote_name
    for table in TABLES:
        for name in ("ilab_order", "ilab_capture", "ilab_no_truncate"):
            schema_editor.execute(f'DROP TRIGGER IF EXISTS {q(name)} ON public.{q(table)}')
    for function in ("order", "capture", "no_truncate"):
        schema_editor.execute(f'DROP FUNCTION IF EXISTS public.ilab_replication_{function}()')


class Migration(migrations.Migration):
    dependencies = [
        ("replication", "0002_infrastructure"),
        ("api", "0053_alter_room_status"),
        ("sessions", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
    ]
    operations = [migrations.RunPython(install, uninstall)]
