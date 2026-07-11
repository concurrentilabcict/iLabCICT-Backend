from django.db import models, transaction, IntegrityError
from api.computer.models import Computer
from django.conf import settings
from api.common.utils.entity_code import generate_entity_code

class MaintenanceHistory(models.Model):

    class MaintenanceTypes(models.TextChoices):
        REPAIR = 'repair', 'repair'
        REPLACE = 'replace', 'replace'
        INSTALLATION = 'installation', 'installation'

    maintenance_history_code = models.CharField(max_length=20, unique=True, null=True)
    computer =  models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='maintenance_history')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    maintenance_type = models.CharField(max_length=20, choices=MaintenanceTypes)
    maintenance_notes = models.TextField()
    performed_by = models.CharField(max_length=50)
    date_performed = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.maintenance_history_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():
                        self.maintenance_history_code = generate_entity_code(
                            model=MaintenanceHistory,
                            field_name="maintenance_history_code",
                            prefix="MH"
                        )
                
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.maintenance_history_code = None

            raise IntegrityError("Failed to generate unique maintenance history code")

