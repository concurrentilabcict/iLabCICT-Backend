from rest_framework.generics import ListAPIView
from api.audit_logs.models import AuditLogs
from api.audit_logs.serializers import AuditLogsSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated


class AuditLogsListView(ListAPIView):
    queryset = AuditLogs.objects.select_related('audit_logs')
    serializer_class = AuditLogsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
