from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.backends.postgresql.psycopg_any import sql
from api.replication.registry import TABLES, TRIGGERS, PROCESS_LOCK
from api.replication.schema import compatible


class Command(BaseCommand):
    help = "Stage B only: enable/disable installed primary capture. Requires a fenced write window."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["enable", "disable"])
        parser.add_argument("--approved-maintenance-window", action="store_true", required=True)

    def handle(self, *args, **options):
        if settings.REPLICATION_ENABLED:
            raise CommandError("Disable processing before changing capture.")
        with transaction.atomic(using="default"), connections["default"].cursor() as c:
            c.execute("SET LOCAL lock_timeout = '5s'")
            c.execute("SET LOCAL statement_timeout = '15s'")
            c.execute("SELECT pg_try_advisory_xact_lock(%s)", [PROCESS_LOCK])
            if not c.fetchone()[0]:
                raise CommandError("Processor is active.")
            for table in TABLES:
                c.execute(sql.SQL("LOCK TABLE public.{} IN ACCESS EXCLUSIVE MODE").format(sql.Identifier(table)))
            if options["action"] == "enable":
                compatible(require_capture=False)
            verb = sql.SQL("ENABLE" if options["action"] == "enable" else "DISABLE")
            for table in TABLES:
                for trigger in TRIGGERS:
                    c.execute(sql.SQL("ALTER TABLE public.{} {} TRIGGER {}").format(sql.Identifier(table), verb, sql.Identifier(trigger)))
        if options.get("verbosity", 1):
            self.stdout.write("Primary capture " + options["action"] + "d. Baseline consistency must be verified separately.")
