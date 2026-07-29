
from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationEntityTypes(models.TextChoices):
        TICKET = 'ticket', 'ticket'
        WEEKLY_REPORT = 'weekly-report', 'weekly-report'
        COMPUTER = 'computer', 'computer'
        USER = 'user', 'user'
        MAINTENANCE_HISTORY = 'maintenance_history', 'maintenance_history'
        ROOM = 'room', 'room'
        REQUEST_HISTORY = 'request_history', 'request_history'
        REPAIR_LOG = 'repair_log', 'repair_log'

    class NotificationStatus(models.TextChoices):
        READ = 'read', 'read'
        UNREAD = 'unread', 'unread'

    class NotificationEventTypes(models.TextChoices):
        BROADCAST_ADMIN_TECHNICIAN = 'broadcast-admin-technician', 'broadcast-admin-technician'
        MULTICAST_ADMIN = 'multicast-admin', 'multicast-admin'
        MULTICAST_TECHNICIAN = 'multicast-technician', 'multicast-technician'
        MULTICAST_FACULTY = 'multicast-faculty', 'multicast-faculty'
        UNICAST_ADMIN = 'unicast-admin', 'unicast-admin'
        UNICAST_TECHNICIAN = 'unicast-technician', 'unicast-technician'
        UNICAST_FACULTY = 'unicast-faculty', 'unicast-faculty'

    recipient_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recepient', blank=True, null=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    entity_type = models.CharField(max_length=20, choices=NotificationEntityTypes, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=NotificationEventTypes, null=True, blank=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    activity_summary = models.JSONField(default=dict,null=True, blank=True)
    status = models.CharField(max_length=20, choices=NotificationStatus, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    

