from django.db import models

class Room(models.Model):
    class RoomStatus(models.TextChoices):
        OPERATIONAL = "operational", "operational"
        MAINTENANCE = "maintenance", "maintenance"
        DEGRADED = "degraded", "degraded"
        OUT_OF_SERVICE = "out_of_service", "out of service"

    room_name = models.CharField(max_length=20)
    floor_number = models.IntegerField()
    computer_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.OPERATIONAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)