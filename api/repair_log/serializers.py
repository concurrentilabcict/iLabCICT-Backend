from rest_framework import serializers
from api.repair_log.models import RepairLog

class RepairLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairLog
        fields = '__all__'
        read_only_fields = ['repair_log_code']