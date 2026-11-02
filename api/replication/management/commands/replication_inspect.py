import json
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from api.replication.schema import catalog, compatible, ReplicationError, reconcile
from api.replication.models import ReplicationEvent
from api.replication.diagnostics import sanitized_event_error


class Command(BaseCommand):
    help = "Read-only database inventory or reconciliation. Does not activate replication."

    def add_arguments(self, parser):
        parser.add_argument("--reconcile", action="store_true")
        parser.add_argument("--events", action="store_true", help="Oldest 50 outstanding event headers, never row data")

    def handle(self, *args, **options):
        if options["events"]:
            with transaction.atomic(using="default"), connections["default"].cursor() as c:
                c.execute("SET TRANSACTION READ ONLY")
                c.execute("SET LOCAL statement_timeout = '5s'")
                headers = list(ReplicationEvent.objects.using("default").exclude(status="APPLIED").order_by("id").values(
                    "id", "event_uuid", "transaction_id", "model_name", "event_type", "status",
                    "attempts", "created_at", "next_retry_at", "last_error")[:50])
                for header in headers:
                    header["last_error"] = sanitized_event_error(header["last_error"])
            self.stdout.write(json.dumps(headers, default=str, indent=2))
            return
        if options["reconcile"]:
            self.stdout.write(json.dumps(reconcile(), default=str, indent=2))
            return
        for alias in ("default", "recovery"):
            with transaction.atomic(using=alias), connections[alias].cursor() as c:
                c.execute("SET TRANSACTION READ ONLY")
                c.execute("SET LOCAL statement_timeout = '10s'")
                info = catalog(alias)
                self.stdout.write(json.dumps({"database": alias, **info}, default=str, indent=2))
        try:
            with transaction.atomic(using="default"), transaction.atomic(using="recovery"):
                for alias in ("default", "recovery"):
                    with connections[alias].cursor() as c:
                        c.execute("SET TRANSACTION READ ONLY")
                        c.execute("SET LOCAL statement_timeout = '10s'")
                compatible(require_capture=False)
            self.stdout.write("Schemas compatible; this does not prove row consistency.")
        except ReplicationError as exc:
            self.stderr.write(exc.code)
