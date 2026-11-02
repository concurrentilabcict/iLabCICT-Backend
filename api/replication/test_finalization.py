"""Regression tests for the final infrastructure audit. Isolated PostgreSQL only."""
import importlib
import io
import json
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.db import connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.query import QuerySet
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from . import tests as fixtures
from .models import AppliedReplicationEvent, ReplicationEvent
from .registry import TABLES, TRIGGERS, PROCESS_LOCK
from .scheduler_baseline import reconcile_scheduler
from .schema import ReplicationError, catalog, compatible, reconcile
from .services import process_pending_events, replication_status


class FinalizationTests(TransactionTestCase):
    databases = {"default", "recovery"}
    setUp = fixtures.ReplicationTests.setUp
    tearDown = fixtures.ReplicationTests.tearDown
    _disable = fixtures.ReplicationTests._disable
    room = fixtures.ReplicationTests.room
    replay = fixtures.ReplicationTests.replay

    def test_allowlist_matches_every_managed_business_and_support_table(self):
        from django.db.migrations.loader import MigrationLoader
        state = MigrationLoader(None).project_state()
        scoped = {model._meta.db_table for model in state.apps.get_models(include_auto_created=True)
                  if model._meta.app_label in {"api", "auth", "contenttypes", "sessions", "admin"} and model._meta.managed}
        migration = importlib.import_module("api.replication.migrations.0003_capture_definitions")
        self.assertEqual(set(TABLES), scoped)
        self.assertEqual(set(TABLES), set(migration.TABLES))
        self.assertEqual(len(TABLES), 22)
        self.assertIn("api_taskscheduler", TABLES)
        self.assertEqual(len(catalog("default")["triggers"]), 22*len(TRIGGERS))

    def test_one_transaction_captures_and_replays_all_22_tables(self):
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import Permission
        with transaction.atomic():
            content_type = ContentType.objects.create(app_label="isolated_replication", model="fixture")
            permission = Permission.objects.create(name="Isolated permission", codename="isolated", content_type=content_type)
            group = fixtures.Group.objects.create(name="isolated-all-tables")
            group.permissions.add(permission)
            user = fixtures.User.objects.create(username="all-tables", email="all@example.invalid", user_code="US-ALL")
            user.groups.add(group)
            user.user_permissions.add(permission)
            room = fixtures.Room.objects.create(room_name="all-tables", floor_number=1, assigned_custodian=user)
            pc = fixtures.Computer.objects.create(room=room, computer_code="PC-ALL", operating_system="test", gpu="test", cpu="test", ram_size_installed=4, disk_size_installed=128, build_version="test", motherboard="test")
            ticket = fixtures.Ticket.objects.create(room=room, computer=pc, reported_by=user, ticket_code="TK-ALL", type="report", title="test", complaint_description="test")
            repair = fixtures.RepairLog.objects.create(ticket=ticket, technician=user, repair_log_code="RL-ALL", title="test", repair_notes="test")
            fixtures.MaintenanceHistory.objects.create(computer=pc, technician=user, repair_log=repair, maintenance_history_code="MH-ALL", maintenance_type="repair", maintenance_notes="test")
            fixtures.Report.objects.create(technician=user, report_code="RP-ALL", title="test", content={}, status="unread")
            fixtures.RequestHistory.objects.create(room=room, technician=user, ticket=ticket, request_history_code="RH-ALL")
            fixtures.Notification.objects.create(recipient_id=user, title="test")
            fixtures.TaskScheduler.objects.create(type="report", frequency="weekly", weekday=1, execution_time=timezone.now().time())
            fixtures.AuditLogs.objects.create(performed_by=user, action_title="test", action_summary="test")
            fixtures.UserPushToken.objects.create(user=user, expo_push_token="isolated-token-not-real")
            fixtures.OTPCode.objects.create(user=user, code_hash="isolated-not-a-real-code", expires_at=timezone.now()+timedelta(hours=1))
            fixtures.PrintableTemplate.objects.create(name="isolated", template_url="https://example.invalid/template", updated_by=user)
            fixtures.Session.objects.create(session_key="isolated-all-tables", session_data="test", expire_date=timezone.now()+timedelta(days=1))
            LogEntry.objects.create(user=user, content_type=content_type, object_id="isolated", object_repr="fixture", action_flag=1)
        self.assertEqual(set(ReplicationEvent.objects.values_list("model_name", flat=True)), set(TABLES))
        self.assertEqual(ReplicationEvent.objects.values("transaction_id").distinct().count(), 1)
        self.replay(22)
        self.assertTrue(all(result["matches"] for result in reconcile().values()))

    def test_partial_receipt_history_blocks_the_entire_transaction(self):
        with transaction.atomic():
            self.room("first")
            self.room("second")
        self.replay(2)
        receipt = AppliedReplicationEvent.objects.using("recovery").first()
        AppliedReplicationEvent.objects.using("recovery").filter(pk=receipt.pk).delete()
        ReplicationEvent.objects.update(status="PENDING")
        result = process_pending_events()
        self.assertEqual(result["error_code"], "PARTIAL_TRANSACTION_RECEIPTS")
        self.assertEqual(fixtures.Room.objects.using("recovery").count(), 2)
        self.assertEqual(ReplicationEvent.objects.filter(status="FAILED").count(), 2)

    def test_actual_source_acknowledgement_failure_recovers_from_receipts(self):
        self.room()
        original = QuerySet.update
        def broken_ack(queryset, **kwargs):
            if queryset.model is ReplicationEvent and kwargs.get("status") == "APPLIED":
                with connections["default"].cursor() as c:
                    c.execute("SELECT 1/0")  # Fail source bookkeeping after Sydney commit.
            return original(queryset, **kwargs)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + settings.REPLICATION_TOKEN)
        with patch.object(QuerySet, "update", new=broken_ack):
            response = client.post("/api/replication/process/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"outcome": "UNAVAILABLE"})
        self.assertEqual(ReplicationEvent.objects.get().status, "PENDING")
        self.assertEqual(AppliedReplicationEvent.objects.using("recovery").count(), 1)
        self.replay(1)
        self.assertEqual(fixtures.Room.objects.using("recovery").count(), 1)

    def test_receipts_are_batched_per_transaction(self):
        with transaction.atomic():
            self.room("first")
            self.room("second")
        with CaptureQueriesContext(connections["recovery"]) as captured:
            self.replay(2)
        reads = [q for q in captured if 'FROM "replication_appliedreplicationevent"' in q["sql"]]
        writes = [q for q in captured if 'INSERT INTO "replication_appliedreplicationevent"' in q["sql"]]
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(writes), 1)

    def test_adjacent_inserts_use_one_strict_bulk_statement(self):
        fixtures.Room.objects.bulk_create([fixtures.Room(room_name=f"batch-{i}", floor_number=i) for i in range(25)])
        with CaptureQueriesContext(connections["recovery"]) as captured:
            self.replay(25)
        inserts = [q for q in captured if q["sql"].startswith('INSERT INTO public."api_room"')]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(fixtures.Room.objects.using("recovery").count(), 25)

    def test_bulk_insert_conflict_rolls_back_all_new_rows(self):
        rooms = fixtures.Room.objects.bulk_create([fixtures.Room(room_name=f"conflict-{i}", floor_number=i) for i in range(2)])
        fixtures.Room.objects.using("recovery").create(pk=rooms[1].pk, room_name="unrelated", floor_number=99)
        self.assertEqual(process_pending_events()["error_code"], "INSERT_CONFLICT")
        self.assertFalse(fixtures.Room.objects.using("recovery").filter(pk=rooms[0].pk).exists())
        self.assertEqual(fixtures.Room.objects.using("recovery").get(pk=rooms[1].pk).floor_number, 99)
        self.assertFalse(AppliedReplicationEvent.objects.using("recovery").exists())

    def test_insert_batching_does_not_reorder_interleaved_updates(self):
        with transaction.atomic():
            room = self.room("first")
            fixtures.Room.objects.filter(pk=room.pk).update(floor_number=7)
            self.room("second")
        self.replay(3)
        self.assertEqual(fixtures.Room.objects.using("recovery").get(pk=room.pk).floor_number, 7)

    def test_atomic_before_image_check_after_waiting_for_target_writer(self):
        from . import services
        from concurrent.futures import ThreadPoolExecutor
        import threading
        room = self.room()
        self.replay(1)
        fixtures.Room.objects.filter(pk=room.pk).update(floor_number=2)
        config = connections["recovery"].settings_dict
        other = fixtures.psycopg2.connect(host=config["HOST"], port=config["PORT"], user=config["USER"], dbname=config["NAME"])
        entered = threading.Event()
        original = services.apply_event
        def signal(*args):
            entered.set()
            return original(*args)
        def worker():
            try:
                return process_pending_events()
            finally:
                connections.close_all()
        try:
            with other.cursor() as c:
                c.execute("UPDATE api_room SET floor_number=99 WHERE id=%s", [room.pk])
            with patch("api.replication.services.apply_event", new=signal), ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker)
                self.assertTrue(entered.wait(5))
                with self.assertRaises(TimeoutError):
                    future.result(timeout=0.2)
                other.commit()
                self.assertEqual(future.result(timeout=5)["error_code"], "BEFORE_IMAGE_CONFLICT")
        finally:
            other.rollback()
            other.close()
        self.assertEqual(fixtures.Room.objects.using("recovery").get(pk=room.pk).floor_number, 99)

    def test_disabled_capture_is_not_reported_as_schema_incompatibility(self):
        self._disable()
        status = replication_status()
        self.assertTrue(status["singapore_connected"])
        self.assertTrue(status["sydney_connected"])
        self.assertTrue(status["schema_compatible"])
        self.assertFalse(status["capture_ready"])
        self.assertFalse(status["processor_running"])

    def test_monitoring_before_infrastructure_migrations(self):
        self._disable()
        try:
            for alias in ("default", "recovery"):
                MigrationExecutor(connections[alias]).migrate([("replication", "0001_initial")])
            status = replication_status()
            self.assertTrue(status["singapore_connected"])
            self.assertTrue(status["sydney_connected"])
            self.assertFalse(status["metrics_available"])
            self.assertIsNone(status["pending_events"])
            self.assertFalse(status["schema_compatible"])
        finally:
            for alias in ("recovery", "default"):
                MigrationExecutor(connections[alias]).migrate([("replication", "0003_capture_definitions")])

    def test_status_reports_processor_lock_and_does_not_write(self):
        config = connections["default"].settings_dict
        other = fixtures.psycopg2.connect(host=config["HOST"], port=config["PORT"], user=config["USER"], dbname=config["NAME"])
        try:
            with other.cursor() as c:
                c.execute("SELECT pg_advisory_xact_lock(%s)", [PROCESS_LOCK])
            with CaptureQueriesContext(connections["default"]) as captured:
                self.assertTrue(replication_status()["processor_running"])
            self.assertFalse(any(q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for q in captured))
        finally:
            other.rollback()
            other.close()
        self.assertFalse(replication_status()["processor_running"])

    def test_status_does_not_call_a_timed_out_schema_check_incompatible(self):
        with patch("api.replication.services.compatible", side_effect=ReplicationError("TIME_BUDGET")):
            status = replication_status()
        self.assertTrue(status["singapore_connected"])
        self.assertTrue(status["sydney_connected"])
        self.assertIsNone(status["schema_compatible"])
        self.assertEqual(status["schema_error_code"], "TIME_BUDGET")

    @override_settings(REPLICATION_BATCH_SIZE=1)
    def test_status_exposes_sanitized_blocked_run_reason(self):
        with transaction.atomic():
            self.room("first")
            self.room("second")
        self.assertEqual(process_pending_events()["outcome"], "BLOCKED")
        self.assertEqual(replication_status()["last_run_error_code"], "TRANSACTION_TOO_LARGE")

    def test_legacy_error_text_is_redacted_from_diagnostics(self):
        self.room()
        ReplicationEvent.objects.update(last_error="connection password=private-credential")
        output = io.StringIO()
        call_command("replication_inspect", events=True, stdout=output)
        self.assertNotIn("private-credential", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())[0]["last_error"], "LEGACY_ERROR_REDACTED")

    def test_child_before_parent_in_a_deferred_source_transaction(self):
        with transaction.atomic():
            room = fixtures.Room.objects.create(room_name="deferred", floor_number=1, assigned_custodian_id=900001)
            fixtures.User.objects.create(id=900001, username="deferred", user_code="US-DEF", email="deferred@example.invalid")
        self.replay(2)
        self.assertEqual(fixtures.Room.objects.using("recovery").get(pk=room.pk).assigned_custodian_id, 900001)

    def test_primary_key_include_columns_are_not_key_attributes(self):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_key) INCLUDE (session_data)")
        try:
            fixtures.Session.objects.create(session_key="included-column", session_data="payload", expire_date=timezone.now())
            self.assertEqual(ReplicationEvent.objects.get().primary_key, {"session_key": "included-column"})
            self.assertEqual(catalog("default")["keys"]["django_session"], ["session_key"])
            self.replay(1)
        finally:
            for alias in ("default", "recovery"):
                with connections[alias].cursor() as c:
                    c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                    c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_key)")

    def test_composite_key_order_comes_from_index_not_physical_columns(self):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_data,session_key)")
        try:
            self.assertEqual(catalog("default")["keys"]["django_session"], ["session_data", "session_key"])
            fixtures.Session.objects.create(session_key="ordered-composite", session_data="part-one", expire_date=timezone.now())
            self.replay(1)
        finally:
            for alias in ("default", "recovery"):
                with connections[alias].cursor() as c:
                    c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                    c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_key)")

    def test_unvalidated_or_unenforced_constraints_are_rejected(self):
        source, target = catalog("default"), catalog("recovery")
        for info in (source, target):
            row = list(info["constraints"][0])
            row[5] = False
            info["constraints"][0] = tuple(row)
        with patch("api.replication.schema.catalog", side_effect=[source, target]):
            with self.assertRaisesMessage(ReplicationError, "UNENFORCED_OR_UNVALIDATED_CONSTRAINT"):
                compatible()

    def test_migration_reinstall_cannot_disable_active_capture(self):
        migration = importlib.import_module("api.replication.migrations.0003_capture_definitions")
        with self.assertRaisesMessage(RuntimeError, "CAPTURE_ALREADY_ACTIVE"):
            with connections["default"].schema_editor() as editor:
                migration.install(None, editor)
        self.room()
        self.assertEqual(ReplicationEvent.objects.count(), 1)

    def test_disabled_migration_install_is_idempotent(self):
        self._disable()
        migration = importlib.import_module("api.replication.migrations.0003_capture_definitions")
        with connections["default"].schema_editor() as editor:
            migration.install(None, editor)
        info = catalog("default")
        self.assertEqual(len(info["triggers"]), 66)
        self.assertTrue(all(row[2] == "D" for row in info["triggers"]))

    def _scheduler_fixture(self):
        self._disable()
        now = timezone.now()
        source = fixtures.TaskScheduler.objects.create(id=42, type="report", frequency="weekly", weekday=1,
                    execution_time=now.time(), last_execution=now, next_execution=now+timedelta(days=7))
        target = fixtures.TaskScheduler.objects.using("recovery").create(id=42, type="report", frequency="weekly", weekday=1,
                    execution_time=source.execution_time, last_execution=now-timedelta(days=7), next_execution=now)
        return source, target

    @override_settings(REPLICATION_ENABLED=False)
    def test_scheduler_dry_run_and_guarded_apply(self):
        source, target = self._scheduler_fixture()
        plan = reconcile_scheduler()
        target.refresh_from_db(using="recovery")
        self.assertNotEqual(target.last_execution, source.last_execution)
        self.assertEqual(plan["changed_columns"], ["last_execution", "next_execution"])
        self.assertNotIn("id", plan)
        with self.assertRaisesMessage(ReplicationError, "EXPLICIT_REPAIR_APPROVAL_REQUIRED"):
            reconcile_scheduler(apply=True)
        result = reconcile_scheduler(apply=True, expected_source=plan["source_fingerprint"],
            expected_target=plan["target_fingerprint"], maintenance_window=True, backup_confirmed=True)
        self.assertEqual(result["rows_updated"], 1)
        target.refresh_from_db(using="recovery")
        self.assertEqual(target.last_execution, source.last_execution)
        self.assertEqual(target.next_execution, source.next_execution)
        self.assertEqual(reconcile_scheduler()["changed_columns"], [])
        self.assertFalse(ReplicationEvent.objects.exists())

    @override_settings(REPLICATION_ENABLED=False)
    def test_scheduler_stale_plan_and_other_field_changes_abort(self):
        source, target = self._scheduler_fixture()
        plan = reconcile_scheduler()
        fixtures.TaskScheduler.objects.filter(pk=source.pk).update(next_execution=timezone.now()+timedelta(days=10))
        with self.assertRaisesMessage(ReplicationError, "SCHEDULER_PLAN_STALE"):
            reconcile_scheduler(apply=True, expected_source=plan["source_fingerprint"],
                expected_target=plan["target_fingerprint"], maintenance_window=True, backup_confirmed=True)
        fixtures.TaskScheduler.objects.using("recovery").filter(pk=target.pk).update(enabled=False)
        with self.assertRaisesMessage(ReplicationError, "SCHEDULER_NON_TIMESTAMP_CONFLICT"):
            reconcile_scheduler()

    def test_scheduler_refuses_enabled_processing(self):
        with self.assertRaisesMessage(ReplicationError, "DISABLE_PROCESSING_FIRST"):
            reconcile_scheduler()

    @override_settings(REPLICATION_ENABLED=False)
    def test_scheduler_refuses_active_capture_or_existing_history(self):
        with self.assertRaisesMessage(ReplicationError, "BOOTSTRAP_REQUIRES_CAPTURE_OFF"):
            reconcile_scheduler()
        self._scheduler_fixture()
        ReplicationEvent.objects.create(event_type="legacy", model_name="legacy", object_id="", payload={})
        with self.assertRaisesMessage(ReplicationError, "BOOTSTRAP_REQUIRES_EMPTY_HISTORY"):
            reconcile_scheduler()

    @override_settings(REPLICATION_ENABLED=False)
    def test_scheduler_refuses_more_than_one_row(self):
        self._scheduler_fixture()
        for alias in ("default", "recovery"):
            fixtures.TaskScheduler.objects.using(alias).create(id=43, type="report", frequency="weekly")
        with self.assertRaisesMessage(ReplicationError, "SCHEDULER_REPAIR_REQUIRES_SINGLE_ROW"):
            reconcile_scheduler()

    @override_settings(REPLICATION_ENABLED=False)
    def test_scheduler_failed_verification_rolls_back_target(self):
        from . import scheduler_baseline
        self._scheduler_fixture()
        plan = reconcile_scheduler()
        source = scheduler_baseline._row("default")
        target = scheduler_baseline._row("recovery")
        bad_result = (*source[:2], "0"*64)
        with patch("api.replication.scheduler_baseline._row", side_effect=[source, target, bad_result]):
            with self.assertRaisesMessage(ReplicationError, "SCHEDULER_REPAIR_VERIFICATION_FAILED"):
                reconcile_scheduler(apply=True, expected_source=plan["source_fingerprint"],
                    expected_target=plan["target_fingerprint"], maintenance_window=True, backup_confirmed=True)
        self.assertEqual(scheduler_baseline._row("recovery")[2], plan["target_fingerprint"])

    def test_sequence_inspection_is_read_only_and_detects_explicit_id_lag(self):
        from .preflight import sequence_check
        fixtures.Room.objects.create(id=500000, room_name="sequence-check", floor_number=1)
        self.replay(1)
        with CaptureQueriesContext(connections["recovery"]) as captured:
            info = sequence_check("recovery")
        room = next(row for row in info if row["table"] == "api_room")
        self.assertTrue(room["promotion_reseed_required"])
        self.assertEqual(len(info), 21)
        self.assertFalse(any("nextval(" in q["sql"].lower() or "setval(" in q["sql"].lower() for q in captured))
