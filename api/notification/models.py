
from django.db import models
from django.conf import settings
from api.ticket.models import Ticket
from api.report.models import Report
from django.db.models import Q

class Notification(models.Model):
    class NotificationTypes(models.TextChoices):
        TICKET = 'ticket', 'ticket'
        REPORT = 'report', 'report'

    class NotificationStatus(models.TextChoices):
        READ = 'read', 'read'
        UNREAD = 'unread', 'unread'

    class TicketTypes(models.TextChoices):
        REQUEST = 'request', 'request'
        REPORT = 'report', 'report'

    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='ticket', blank=True, null=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='report', blank=True, null=True)

    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=TicketTypes, default=NotificationTypes.TICKET)
    status = models.CharField(max_length=20, choices=NotificationStatus, default=NotificationStatus.UNREAD)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(ticket__isnull=False) & Q(report__isnull=True))
                    |
                    (Q(ticket__isnull=True) & Q(report__isnull=False))
                ),
                name='notif_one_ref'
            )
        ]
    

