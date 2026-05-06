from django.db import models
from api.room.models import Room

class Computer(models.Model):
    class PeripheralStatus(models.TextChoices):
        NONE = "none", "none"
        ACTIVE = "active", "active"
        FIXING = "fixing", "fixing"
        BROKEN = "broken", "broken"

    class ComputerStatus(models.TextChoices):
        ACTIVE = "active", "active"
        FIXING = "fixing", "fixing"
        BROKEN = "broken", "broken"
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='computers')
    computer_code = models.CharField(max_length=20, unique=True)
    operating_system = models.CharField(max_length=30)
    gpu = models.CharField(max_length=30)
    cpu = models.CharField(max_length=30)
    ram_size_installed = models.IntegerField()
    disk_size_installed = models.IntegerField()
    build_version = models.CharField(max_length=30)
    computer_status = models.CharField(max_length=20, choices=ComputerStatus.choices, default=ComputerStatus.ACTIVE)

    # peripherals
    monitor_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    mouse_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    keyboard_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    ups_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
