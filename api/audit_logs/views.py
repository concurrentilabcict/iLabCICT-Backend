from rest_framework.generics import ListAPIView
from api.audit_logs.serializers import AuditLogsSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated
from api.paginations import AuditLogPagination
from api.audit_logs.services import AuditLogsService
from django.db.models import Q

class AuditLogsListView(ListAPIView):
    serializer_class = AuditLogsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        queryset = AuditLogsService.get_all(user=self.request.user)

        before_id = self.request.query_params.get('before_id')

        before_created_at = self.request.query_params.get('before_created_at')

        if before_created_at and before_id:
            queryset = queryset.filter(
                Q(created_at__lt=before_created_at) |
                Q(
                    created_at=before_created_at,
                    id__lt=before_id
                )
            )

        return queryset