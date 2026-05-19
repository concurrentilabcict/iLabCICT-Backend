from django.db import models
from api.computer.models import Computer
from django.conf import settings

class MaintenanceHistory(models.Model):

    class MaintenanceTypes(models.TextChoices):
        REPAIR = 'repair', 'Repair'
        INSPECTION = 'inspection', 'Inspection'
        UPGRADE = 'upgrade', 'Upgrade'
        INSTALLATION = 'installation', 'Installation'

    computer =  models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='maintenance_history')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    maintenance_type = models.CharField(max_length=20, choices=MaintenanceTypes)
    maintenance_notes = models.TextField()
    performed_by = models.CharField(max_length=50)
    date_performed = models.DateTimeField(auto_now_add=True)

