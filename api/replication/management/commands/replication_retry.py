from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from api.replication.models import ReplicationEvent
from api.replication.registry import PROCESS_LOCK


class Command(BaseCommand):
    help = "Requeue one diagnosed transaction; never skip, edit, or delete its payloads."

    def add_arguments(self, parser):
        parser.add_argument("transaction_id")
        parser.add_argument("--conflict-resolved", action="store_true", required=True)

    def handle(self, *args, **options):
        with transaction.atomic(using="default"), connections["default"].cursor() as c:
            c.execute("SELECT pg_try_advisory_xact_lock(%s)", [PROCESS_LOCK])
            if not c.fetchone()[0]:
                raise CommandError("Processor is active.")
            events = ReplicationEvent.objects.using("default").filter(transaction_id=options["transaction_id"]).exclude(status="APPLIED")
            if not events.exists():
                raise CommandError("No unapplied transaction found.")
            count = events.update(status="PENDING", attempts=0, next_retry_at=None, last_error=None)
        self.stdout.write(f"Requeued {count} events. Receipts remain authoritative.")
