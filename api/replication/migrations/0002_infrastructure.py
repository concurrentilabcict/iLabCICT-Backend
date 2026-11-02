import uuid
from django.db import migrations, models


def fill_uuids(apps, schema_editor):
    Event = apps.get_model("replication", "ReplicationEvent")
    for pk in Event.objects.using(schema_editor.connection.alias).values_list("pk", flat=True).iterator():
        Event.objects.using(schema_editor.connection.alias).filter(pk=pk).update(event_uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("replication", "0001_initial")]
    operations = [
        migrations.AddField("replicationevent", "event_uuid", models.UUIDField(null=True)),
        migrations.RunPython(fill_uuids, migrations.RunPython.noop),
        migrations.AlterField("replicationevent", "event_uuid", models.UUIDField(default=uuid.uuid4, unique=True)),
        migrations.AddField("replicationevent", "transaction_id", models.CharField(max_length=32, default="", db_index=True)),
        migrations.AddField("replicationevent", "primary_key", models.JSONField(default=dict)),
        migrations.AddField("replicationevent", "old_row", models.JSONField(null=True)),
        migrations.AddField("replicationevent", "next_retry_at", models.DateTimeField(null=True)),
        migrations.AddField("appliedreplicationevent", "digest", models.CharField(max_length=64, default="")),
        migrations.AddIndex("replicationevent", models.Index(fields=["id"], condition=~models.Q(status="APPLIED"), name="replication_outstanding_idx")),
        migrations.CreateModel(name="ReplicationRun", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("started_at", models.DateTimeField(auto_now_add=True)),
            ("finished_at", models.DateTimeField(null=True)),
            ("duration_seconds", models.FloatField(default=0)),
            ("applied", models.PositiveIntegerField(default=0)),
            ("outcome", models.CharField(max_length=32, default="RUNNING")),
            ("error_code", models.CharField(max_length=64, default="")),
        ]),
    ]
