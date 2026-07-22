from django.db import models, transaction, IntegrityError
from api.room.models import Room
from api.ticket.models import Ticket
from api.common.utils.entity_code import generate_entity_code
from django.conf import settings
class RequestHistory(models.Model):

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='request_history')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_performed = models.DateTimeField(auto_now_add=True)
    request_history_code = models.CharField(max_length=20, unique=True, null=True)
    request_notes = models.TextField()

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='request_history_ticket', null=True)

    def save(self, *args, **kwargs):
        if self.request_history_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():
                        self.request_history_code = generate_entity_code(
                            model=RequestHistory,
                            field_name='request_history_code',
                            prefix='RH'
                        )

                        return super().save(*args, **kwargs)
                    
                except IntegrityError:
                    self.request_history_code = None

            raise IntegrityError("Failed to generate unique request history code")