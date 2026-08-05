from rest_framework import serializers
from api.audit_logs.models import AuditLogs
from api.user.serializers import UserMinimalSerializer
class AuditLogsSerializer(serializers.ModelSerializer):

    performed_by = UserMinimalSerializer()

    class Meta:
        model = AuditLogs
        fields = '__all__'

