from django.db import models

class Room(models.Model):
    class RoomStatus(models.TextChoices):
        OPERATIONAL = "operational", "operational"
        MAINTENANCE = "maintenance", "maintenance"
        DEGRADED = "degraded", "degraded"
        OUT_OF_SERVICE = "out_of_service", "out of service"

    class BuildingName(models.TextChoices):
        PIMENTEL = "pimentel", "pimentel"
        LAW = "law", "law"
        ACAD = "acad", "acad"

    building_name = models.CharField(max_length=20, choices=BuildingName.choices, default=BuildingName.PIMENTEL)
    room_name = models.CharField(max_length=20, unique=True)
    floor_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.OPERATIONAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)