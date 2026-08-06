from django.db import models
from django.conf import settings

class AuditLogs(models.Model):
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action_title = models.CharField(max_length=100)
    action_summary = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)