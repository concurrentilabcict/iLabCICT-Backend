
from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationStatus(models.TextChoices):
        READ = 'read', 'read'
        UNREAD = 'unread', 'unread'

    class TicketTypes(models.TextChoices):
        REQUEST = 'request', 'request'
        REPORT = 'report', 'report'

    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=120)
    header = models.TextField(default="")
    ticket_type = models.CharField(max_length=20, choices=TicketTypes, default=TicketTypes.REQUEST)
    status = models.CharField(max_length=20, choices=NotificationStatus, default=NotificationStatus.UNREAD)
    created_at = models.DateTimeField(auto_now_add=True)

