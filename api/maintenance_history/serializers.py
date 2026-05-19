from rest_framework import serializers
from api.maintenance_history.models import MaintenanceHistory

class MaintenanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceHistory
        fields = '__all__'