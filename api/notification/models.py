
from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationStatus(models.TextChoices):
        READ = 'read', 'Read'
        UNREAD = 'unread', 'Unread'

    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=120)
    content = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=NotificationStatus)
    created_at = models.DateTimeField(auto_now_add=True)
