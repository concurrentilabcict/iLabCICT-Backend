from django.db import models
from django.conf import settings
from api.computer.models import Computer
from api.room.models import Room

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

    type = models.CharField(max_length=12, choices=TicketType.choices)
    title = models.CharField(max_length=100)
    complaint_description = models.TextField()
    issue_image = models.ImageField(upload_to="tickets/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)