from rest_framework import serializers
from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory

class RepairLogSerializer(serializers.ModelSerializer):

    maintenance_type = serializers.CharField(
        choices = MaintenanceHistory.MaintenanceTypes.choices,
        write_only = True)

    class Meta:
        model = RepairLog
        fields = '__all__'
        read_only_fields = ['repair_log_code']