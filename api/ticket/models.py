from django.db import models

class Ticket(models.Model):
    class TicketStatus(models.TextChoices):
        OPEN = "open", "open"
        PENDING = "pending", "pending"
        RESOLVED = "resolved", "resolved"
        
    title = models.CharField(max_length=100)
    complaint_description = models.TextField()

    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)