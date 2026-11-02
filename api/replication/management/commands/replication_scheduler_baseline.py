import json

from django.core.management.base import BaseCommand, CommandError
from api.replication.scheduler_baseline import reconcile_scheduler
from api.replication.schema import ReplicationError


class Command(BaseCommand):
    help = "Read-only scheduler baseline plan; explicit --apply is operator-only production DML."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--expected-source")
        parser.add_argument("--expected-target")
        parser.add_argument("--approved-maintenance-window", action="store_true")
        parser.add_argument("--backup-confirmed", action="store_true")

    def handle(self, *args, **options):
        try:
            result = reconcile_scheduler(
                apply=options["apply"], expected_source=options["expected_source"], expected_target=options["expected_target"],
                maintenance_window=options["approved_maintenance_window"], backup_confirmed=options["backup_confirmed"])
        except ReplicationError as exc:
            raise CommandError(exc.code) from None
        except Exception:
            raise CommandError("SCHEDULER_REPAIR_UNAVAILABLE") from None
        self.stdout.write(json.dumps(result, indent=2))
