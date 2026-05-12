from django.db import models, transaction, IntegrityError
from django.conf import settings

from api.computer.models import Computer
from api.room.models import Room
from api.common.utils.entity_code import generate_entity_code

class Ticket(models.Model):
    class TicketStatus(models.TextChoices):
        OPEN = "open", "open"
        PENDING = "pending", "pending"
        RESOLVED = "resolved", "resolved"
        
    class TicketType(models.TextChoices):
        REPORT = "report", "report"
        REQUEST = "request", "request"    

    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reported_tickets")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="tickets")
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE, related_name="tickets")

    ticket_code = models.CharField(max_length=20, unique=True)

    type = models.CharField(max_length=12, choices=TicketType.choices)
    title = models.CharField(max_length=100)
    complaint_description = models.TextField()
    issue_image = models.ImageField(upload_to="tickets/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.ticket_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5
            
            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():

                        self.ticket_code = generate_entity_code(
                            model=Ticket,
                            field_name="ticket_code",
                            prefix="TK",
                            )
                        
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.ticket_code = None

            raise IntegrityError("Failed to generate unique ticket code")