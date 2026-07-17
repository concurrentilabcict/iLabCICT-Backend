from rest_framework import serializers
from api.maintenance_history.models import MaintenanceHistory
from api.repair_log.serializers import RepairLogReadSerializer
from api.computer.serializers import ComputerMinimalSerializer

class MaintenanceHistorySerializer(serializers.ModelSerializer):

    repair_log = RepairLogReadSerializer(read_only=True)
    computer = ComputerMinimalSerializer()

    class Meta:
        model = MaintenanceHistory
        fields = '__all__'