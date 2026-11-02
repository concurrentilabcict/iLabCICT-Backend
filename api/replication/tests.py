import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import psycopg2
from django.conf import settings
from django.core.management import call_command
from django.db import connections, transaction, OperationalError
from django.test import TransactionTestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

if settings.SETTINGS_MODULE != "api.replication.test_settings":
    raise RuntimeError("Replication tests require --settings=api.replication.test_settings; production settings are forbidden.")

# Load every business model for the ORM's existing cascade collector in tests.
from api.user.models import User
from api.room.models import Room
from api.computer.models import Computer
from api.ticket.models import Ticket
from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.notification.models import Notification
from api.otp_code.models import OTPCode
from api.printable_template.models import PrintableTemplate
from api.report.models import Report
from api.request_history.models import RequestHistory
from api.task_scheduler.models import TaskScheduler
from api.audit_logs.models import AuditLogs
from api.user_push_token.models import UserPushToken
from django.contrib.sessions.models import Session
from django.contrib.auth.models import Group

from .models import ReplicationEvent, AppliedReplicationEvent
from .registry import TABLES, TRIGGERS, PROCESS_LOCK
from .schema import catalog, reconcile, ReplicationError, schema_signature
from .services import process_pending_events, replication_status, _apply_group


class EndpointTests(SimpleTestCase):
    def test_schema_signature_handles_postgres_18_and_column_order(self):
        source = {"columns": [("example", "id", "integer", True, "d", "", None, 1),
                              ("example", "name", "text", False, "", "", None, 3)],
                  "constraints": [("example", "p", "PRIMARY KEY (id)", False, False, True, True)],
                  "indexes": [], "migrations": [], "keys": {"example": ["id"]}}
        import copy
        target = copy.deepcopy(source)
        target["columns"] = [(*source["columns"][1][:-1], 1), (*source["columns"][0][:-1], 2)]
        target["constraints"].append(("example", "n", "NOT NULL id", False, False, True, True))
        self.assertEqual(schema_signature(source), schema_signature(target))
        changed = list(target["columns"][0])
        changed[3] = True
        target["columns"][0] = tuple(changed)
        self.assertNotEqual(schema_signature(source), schema_signature(target))

    def test_unauthorized_process_and_status(self):
        for method, path in (("post", "process"), ("get", "status")):
            response = getattr(APIClient(), method)(f"/api/replication/{path}/")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response["Cache-Control"], "no-store")

    @override_settings(REPLICATION_TOKEN="")
    def test_missing_secret_fails_closed(self):
        response = APIClient().get("/api/replication/status/", HTTP_AUTHORIZATION="Bearer ")
        self.assertEqual(response.status_code, 401)

    @override_settings(REPLICATION_ENABLED=False)
    def test_disabled_and_reject_parameters(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + settings.REPLICATION_TOKEN)
        self.assertEqual(client.post("/api/replication/process/", {}, format="json").json()["outcome"], "DISABLED")
        self.assertEqual(client.post("/api/replication/process/", {"table": "api_user"}, format="json").status_code, 400)
        self.assertEqual(client.post("/api/replication/process/?limit=999").status_code, 400)


class ReplicationTests(TransactionTestCase):
    databases = {"default", "recovery"}

    @override_settings(REPLICATION_ENABLED=False)
    def setUp(self):
        # These checks make accidental execution under production settings fail
        # before the test's capture activation or business test writes.
        for alias in self.databases:
            config = connections[alias].settings_dict
            self.assertEqual(config["HOST"], "127.0.0.1")
            self.assertEqual(str(config["PORT"]), "55483")
            self.assertTrue(config["NAME"].startswith("test_ilab_replication_"))
        call_command("replication_capture", "enable", approved_maintenance_window=True, verbosity=0)

    @override_settings(REPLICATION_ENABLED=False)
    def _disable(self):
        call_command("replication_capture", "disable", approved_maintenance_window=True, verbosity=0)

    def tearDown(self):
        self._disable()  # Django flush is allowed only after test capture is off.

    def room(self, name="R1"):
        return Room.objects.create(room_name=name, floor_number=1)

    def replay(self, count=None):
        result = process_pending_events()
        self.assertEqual(result["outcome"], "OK", result)
        if count is not None:
            self.assertEqual(result["applied"], count)
        return result

    def test_insert_update_delete_and_unchanged_update(self):
        room = self.room()
        self.replay(1)
        self.assertEqual(Room.objects.using("recovery").get(pk=room.pk).room_name, "R1")
        Room.objects.filter(pk=room.pk).update(floor_number=2)
        self.replay(1)
        self.assertEqual(Room.objects.using("recovery").get(pk=room.pk).floor_number, 2)
        before = ReplicationEvent.objects.count()
        Room.objects.filter(pk=room.pk).update(floor_number=2)
        self.assertEqual(ReplicationEvent.objects.count(), before)
        room.delete()
        self.replay(1)
        self.assertFalse(Room.objects.using("recovery").exists())

    def test_bulk_and_direct_sql_capture(self):
        Room.objects.bulk_create([Room(room_name=f"R{i}", floor_number=i) for i in range(5)])
        self.replay(5)
        Room.objects.all().update(floor_number=8)
        self.replay(5)
        with connections["default"].cursor() as c:
            c.execute("UPDATE api_room SET floor_number=9")
        self.replay(5)
        self.assertEqual(set(Room.objects.using("recovery").values_list("floor_number", flat=True)), {9})

    def test_source_rollback_leaves_no_event(self):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                self.room()
                raise ValueError("roll back")
        self.assertFalse(ReplicationEvent.objects.exists())
        self.replay(0)

    def test_json_numbers_replayed_without_precision_loss(self):
        with connections["default"].cursor() as c:
            c.execute("INSERT INTO api_auditlogs(action_title,action_summary,metadata,created_at) VALUES ('precision','test', %s::jsonb, now())", ['{"value":123456789.123456789123456789}'])
        self.replay(1)
        values = []
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("SELECT metadata::text FROM api_auditlogs")
                values.append(c.fetchone()[0])
        self.assertEqual(values[0], values[1])

    def test_primary_key_update_and_insert_conflict(self):
        room = self.room()
        self.replay(1)
        Room.objects.filter(pk=room.pk).update(id=room.pk+1000)
        self.replay(1)
        self.assertTrue(Room.objects.using("recovery").filter(pk=room.pk+1000).exists())
        source = self.room("conflict")
        Room.objects.using("recovery").create(pk=source.pk, room_name="conflict", floor_number=5)
        self.assertEqual(process_pending_events()["error_code"], "INSERT_CONFLICT")

    @override_settings(REPLICATION_MAX_ATTEMPTS=1)
    def test_retry_exhaustion_is_durable(self):
        self.room()
        with patch("api.replication.services._apply_group", side_effect=OperationalError("offline")):
            self.assertEqual(process_pending_events()["outcome"], "BLOCKED")
        self.assertEqual(ReplicationEvent.objects.get().status, "FAILED")
        self.assertEqual(process_pending_events()["error_code"], "FAILED_HEAD")

    def test_time_budget_rolls_back_target_transaction(self):
        import time
        from .services import _apply_group
        self.room()
        event = ReplicationEvent.objects.get()
        with self.assertRaisesMessage(ReplicationError, "TIME_BUDGET"):
            _apply_group([event], catalog("default"), time.monotonic()-1)
        self.assertFalse(Room.objects.using("recovery").exists())

    def test_cached_outbox_sequence_is_rejected(self):
        with connections["default"].cursor() as c:
            c.execute("ALTER SEQUENCE replication_replicationevent_id_seq CACHE 2")
        try:
            self.assertEqual(process_pending_events()["error_code"], "UNSAFE_OUTBOX_SEQUENCE")
        finally:
            with connections["default"].cursor() as c:
                c.execute("ALTER SEQUENCE replication_replicationevent_id_seq CACHE 1")

    def test_foreign_keys_and_orm_cascades_preserve_whole_transaction(self):
        with transaction.atomic():
            user = User.objects.create(username="tester", user_code="US-TEST", email="test@example.invalid")
            room = Room.objects.create(room_name="R1", floor_number=1, assigned_custodian=user)
            pc = Computer.objects.create(room=room, computer_code="PC-TEST", operating_system="test", gpu="test", cpu="test", ram_size_installed=4, disk_size_installed=128, build_version="test", motherboard="test")
            ticket = Ticket.objects.create(room=room, computer=pc, reported_by=user, ticket_code="TK-TEST", type="report", title="test", complaint_description="test")
            repair = RepairLog.objects.create(ticket=ticket, technician=user, repair_log_code="RL-TEST", title="test", repair_notes="test")
            MaintenanceHistory.objects.create(computer=pc, technician=user, repair_log=repair, maintenance_history_code="MH-TEST", maintenance_type="repair", maintenance_notes="test")
        self.assertEqual(ReplicationEvent.objects.values("transaction_id").distinct().count(), 1)
        self.replay(6)
        user.delete()
        self.replay()
        self.assertFalse(Ticket.objects.using("recovery").exists())
        self.assertFalse(MaintenanceHistory.objects.using("recovery").exists())

    def test_string_primary_key(self):
        Session.objects.create(session_key="non-integer-primary-key", session_data="test", expire_date=timezone.now()+timedelta(days=1))
        self.replay(1)
        self.assertTrue(Session.objects.using("recovery").filter(pk="non-integer-primary-key").exists())

    def test_uuid_primary_key_using_isolated_schema(self):
        import uuid
        from django.db.backends.postgresql.psycopg_any import sql
        # Session has no incoming FK. Change only the disposable test schemas.
        pattern_indexes = {}
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='django_session' AND indexdef LIKE '%varchar_pattern_ops%'")
                pattern_indexes[alias] = c.fetchall()
                for name, definition in pattern_indexes[alias]:
                    c.execute(sql.SQL("DROP INDEX public.{}").format(sql.Identifier(name)))
                c.execute("ALTER TABLE django_session ALTER COLUMN session_key TYPE uuid USING session_key::uuid")
        try:
            key = str(uuid.uuid4())
            with connections["default"].cursor() as c:
                c.execute("INSERT INTO django_session VALUES (%s, 'uuid-test', now())", [key])
            self.replay(1)
            with connections["recovery"].cursor() as c:
                c.execute("SELECT session_key::text FROM django_session")
                self.assertEqual(c.fetchone()[0], key)
        finally:
            for alias in ("default", "recovery"):
                with connections[alias].cursor() as c:
                    c.execute("ALTER TABLE django_session ALTER COLUMN session_key TYPE varchar(40) USING session_key::text")
                    for name, definition in pattern_indexes[alias]:
                        c.execute(definition)

    def test_composite_primary_key_using_isolated_schema(self):
        for alias in ("default", "recovery"):
            with connections[alias].cursor() as c:
                c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_key,session_data)")
        try:
            Session.objects.create(session_key="composite-key", session_data="second-part", expire_date=timezone.now())
            self.assertEqual(ReplicationEvent.objects.get().primary_key, {"session_key": "composite-key", "session_data": "second-part"})
            self.replay(1)
            self.assertEqual(Session.objects.using("recovery").get().session_data, "second-part")
        finally:
            for alias in ("default", "recovery"):
                with connections[alias].cursor() as c:
                    c.execute("ALTER TABLE django_session DROP CONSTRAINT django_session_pkey")
                    c.execute("ALTER TABLE django_session ADD PRIMARY KEY (session_key)")

    def test_many_to_many_join_capture(self):
        with transaction.atomic():
            user = User.objects.create(username="m2m", user_code="US-M2M", email="m2m@example.invalid")
            group = Group.objects.create(name="replication-test-group")
            user.groups.add(group)
        self.replay(3)
        self.assertTrue(User.objects.using("recovery").get(pk=user.pk).groups.filter(pk=group.pk).exists())

    def test_authenticated_status(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + settings.REPLICATION_TOKEN)
        response = client.get("/api/replication/status/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["schema_compatible"])
        self.assertFalse(response.json()["consistency_verified"])

    def test_operator_event_diagnostics_exclude_payloads(self):
        from io import StringIO
        self.room()
        output = StringIO()
        call_command("replication_inspect", events=True, stdout=output)
        header = json.loads(output.getvalue())[0]
        self.assertEqual(header["model_name"], "api_room")
        self.assertNotIn("payload", header)
        self.assertNotIn("primary_key", header)

    def test_duplicate_delivery_after_lost_acknowledgement(self):
        self.room()
        self.replay(1)
        ReplicationEvent.objects.update(status="PENDING", applied_at=None)
        self.replay(1)
        self.assertEqual(AppliedReplicationEvent.objects.using("recovery").count(), 1)
        self.assertEqual(Room.objects.using("recovery").count(), 1)

    def test_receipt_tampering_blocks(self):
        self.room()
        self.replay()
        event = ReplicationEvent.objects.get()
        event.payload["floor_number"] = 88
        event.status = "PENDING"
        event.save()
        self.assertEqual(process_pending_events()["error_code"], "RECEIPT_MISMATCH")

    def test_conflict_does_not_overwrite_and_blocks_later_transactions(self):
        room = self.room()
        self.replay()
        Room.objects.using("recovery").filter(pk=room.pk).update(floor_number=99)
        Room.objects.filter(pk=room.pk).update(floor_number=2)
        self.room("later")
        result = process_pending_events()
        self.assertEqual(result["error_code"], "BEFORE_IMAGE_CONFLICT")
        self.assertEqual(Room.objects.using("recovery").get(pk=room.pk).floor_number, 99)
        self.assertFalse(Room.objects.using("recovery").filter(room_name="later").exists())
        self.assertEqual(process_pending_events()["error_code"], "FAILED_HEAD")

    def test_transaction_target_rollback(self):
        with transaction.atomic():
            self.room("first")
            self.room("second")
        event = ReplicationEvent.objects.order_by("id").last()
        event.payload["assigned_custodian_id"] = 999999
        event.save()
        self.assertEqual(process_pending_events()["outcome"], "BLOCKED")
        self.assertEqual(Room.objects.using("recovery").count(), 0)
        self.assertEqual(AppliedReplicationEvent.objects.using("recovery").count(), 0)

    def test_transient_retry_and_retry_command(self):
        self.room()
        with patch("api.replication.services._apply_group", side_effect=OperationalError("secret connection detail")):
            result = process_pending_events()
        self.assertEqual(result["outcome"], "RETRY")
        event = ReplicationEvent.objects.get()
        self.assertEqual(event.attempts, 1)
        self.assertEqual(event.last_error, "TRANSIENT_DATABASE")
        self.assertEqual(process_pending_events()["outcome"], "RETRY_WAIT")
        call_command("replication_retry", event.transaction_id, conflict_resolved=True)
        self.replay(1)

    def test_recovery_unavailable_and_status_sanitized(self):
        self.room()
        with patch.object(connections["recovery"], "cursor", side_effect=OperationalError("secret password")):
            self.assertEqual(process_pending_events()["outcome"], "UNAVAILABLE")
            status = replication_status()
        self.assertFalse(status["sydney_connected"])
        self.assertNotIn("secret", json.dumps(status, default=str))
        self.assertEqual(ReplicationEvent.objects.get().status, "PENDING")

    def test_overlapping_processor_lock(self):
        self.room()
        config = connections["default"].settings_dict
        other = psycopg2.connect(host=config["HOST"], port=config["PORT"], user=config["USER"], dbname=config["NAME"])
        try:
            with other.cursor() as c:
                c.execute("SELECT pg_advisory_xact_lock(%s)", [PROCESS_LOCK])
            self.assertEqual(process_pending_events()["outcome"], "BUSY")
        finally:
            other.rollback()
            other.close()
        self.replay(1)

    def test_concurrent_capture_uses_commit_order(self):
        entered = threading.Event()
        def later():
            try:
                entered.set()
                self.room("second")
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                self.room("first")
                future = pool.submit(later)
                self.assertTrue(entered.wait(2))
                with self.assertRaises(TimeoutError):
                    future.result(timeout=0.2)
            future.result(timeout=5)
        self.replay(2)
        self.assertEqual(list(ReplicationEvent.objects.order_by("id").values_list("payload__room_name", flat=True)), ["first", "second"])

    def test_schema_mismatch_fails_before_replay(self):
        self.room()
        with connections["recovery"].cursor() as c:
            c.execute("ALTER TABLE api_room ADD COLUMN replication_test_extra integer")
        try:
            self.assertEqual(process_pending_events()["error_code"], "SCHEMA_MISMATCH")
        finally:
            with connections["recovery"].cursor() as c:
                c.execute("ALTER TABLE api_room DROP COLUMN replication_test_extra")
        self.replay(1)

    def test_infrastructure_schema_mismatch_fails_closed(self):
        self.room()
        with connections["recovery"].cursor() as c:
            c.execute("ALTER TABLE replication_appliedreplicationevent ADD COLUMN test_drift integer")
        try:
            self.assertEqual(process_pending_events()["error_code"], "SCHEMA_MISMATCH")
        finally:
            with connections["recovery"].cursor() as c:
                c.execute("ALTER TABLE replication_appliedreplicationevent DROP COLUMN test_drift")
        self.replay(1)

    def test_capture_configuration_drift_fails_closed(self):
        self.room()
        with connections["default"].cursor() as c:
            c.execute("ALTER FUNCTION public.ilab_replication_capture() SET timezone = 'Asia/Manila'")
        try:
            self.assertEqual(process_pending_events()["error_code"], "CAPTURE_DEFINITION_MISMATCH")
        finally:
            with connections["default"].cursor() as c:
                c.execute("ALTER FUNCTION public.ilab_replication_capture() SET timezone = 'UTC'")
        self.replay(1)

    @override_settings(REPLICATION_BATCH_SIZE=1)
    def test_oversized_transaction_not_split(self):
        with transaction.atomic():
            self.room("first")
            self.room("second")
        self.assertEqual(process_pending_events()["error_code"], "TRANSACTION_TOO_LARGE")
        self.assertFalse(Room.objects.using("recovery").exists())

    def test_sydney_has_no_capture_triggers_and_reconciliation_detects_divergence(self):
        self.assertEqual(catalog("recovery")["triggers"], [])
        self.room()
        with self.assertRaises(ReplicationError):
            reconcile()
        self.replay()
        self.assertTrue(reconcile()["api_room"]["matches"])
        Room.objects.using("recovery").update(floor_number=77)
        self.assertFalse(reconcile()["api_room"]["matches"])
