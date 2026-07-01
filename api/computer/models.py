from django.db import models, transaction, IntegrityError
from api.room.models import Room
from api.common.utils.entity_code import generate_entity_code

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
    motherboard = models.CharField(max_length=100)

    # peripherals
    monitor_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    mouse_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    keyboard_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)
    ups_status = models.CharField(max_length=20, choices=PeripheralStatus.choices, default=PeripheralStatus.NONE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.computer_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():
                        self.computer_code = generate_entity_code(
                            model=Computer,
                            field_name="computer_code",
                            prefix="PC"
                        )

                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.computer_code = None
                    
            raise IntegrityError("Failed to generate unique computer code")
