import uuid

from django.db import models

class ReplicationEvent(models.Model):

    class ReplicationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPLIED = "APPLIED", "Applied"
        FAILED = "FAILED", "Failed"

    event_type = models.CharField(max_length=100)

    event_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    transaction_id = models.CharField(max_length=32, default="", db_index=True)
    primary_key = models.JSONField(default=dict)
    old_row = models.JSONField(null=True)
    next_retry_at = models.DateTimeField(null=True)

    model_name = models.CharField(max_length=100)

    object_id = models.CharField(max_length=100)

    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=ReplicationStatus.choices,
        default=ReplicationStatus.PENDING,
        db_index=True,
    )

    attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    applied_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_error = models.TextField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["id"], condition=~models.Q(status="APPLIED"), name="replication_outstanding_idx"),
            models.Index(
                fields=["status", "created_at"],
                name="replication_pending_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.status}"

class AppliedReplicationEvent(models.Model):

    event_id = models.UUIDField(
        primary_key=True,
    )

    applied_at = models.DateTimeField(
        auto_now_add=True,
    )

    digest = models.CharField(max_length=64, default="")

    def __str__(self):
        return str(self.event_id)


class ReplicationRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    duration_seconds = models.FloatField(default=0)
    applied = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=32, default="RUNNING")
    error_code = models.CharField(max_length=64, default="")
