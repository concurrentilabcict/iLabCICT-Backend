from django.db import models, transaction, IntegrityError
from django.conf import settings

from api.ticket.models import Ticket
from api.common.utils.entity_code import generate_entity_code

class RepairLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="repair_logs")
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    repair_log_code = models.CharField(max_length=20, unique=True)

    title = models.CharField(max_length=100)
    repair_notes = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.repair_log_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():
                        self.repair_log_code = generate_entity_code(
                            model=RepairLog,
                            field_name="repair_log_code",
                            prefix="RL"
                        )
                
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.repair_log_code = None

            raise IntegrityError("Failed to generate unique repair log code")