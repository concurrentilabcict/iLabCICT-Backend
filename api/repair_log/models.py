from django.db import models
from api.ticket.models import Ticket
from django.conf import settings

from django.utils import timezone

class RepairLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="repair_logs")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    repair_log_code = models.CharField(max_length=20, unique=True)

    title = models.CharField(max_length=100)
    repair_notes = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.repair_log_code:
            current_year = timezone.now().year

            last_log = RepairLog.objects.filter(repair_log_code__startswith=f"RL{current_year}").order_by("id").last()

            if last_log:
                last_number = int(last_log.repair_log_code[-5:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.repair_log_code = f"{current_year}{new_number:05d}"
        
        super().save(*args, **kwargs)