from rest_framework.generics import ListAPIView
from api.audit_logs.serializers import AuditLogsSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated
from api.audit_logs.services import AuditLogsService
from django.utils.dateparse import parse_datetime
from api.audit_logs.models import AuditLogs
from rest_framework.response import Response
from django.db.models import Q

class AuditLogsListView(ListAPIView):
    serializer_class = AuditLogsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    PAGE_SIZE = 50

    def get_queryset(self):
        queryset = AuditLogsService.get_all(user=self.request.user)

        before_id = self.request.query_params.get('before-id')

        before_created_at = self.request.query_params.get('before-created-at')

        if before_created_at and before_id:

            before_created_at = parse_datetime(before_created_at)

            queryset = queryset.filter(
                Q(created_at__lt=before_created_at) |
                Q(
                    created_at=before_created_at,
                    id__lt=before_id
                )
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()


        logs = list(queryset[:self.PAGE_SIZE + 1])

        has_more = len(logs) > self.PAGE_SIZE
        logs = logs[:self.PAGE_SIZE]

        serializer = self.get_serializer(logs, many=True)

        next_url = None
        if has_more and logs:
            last = logs[-1]

            next_url = (
                f'{request.build_absolute_uri(request.path)}'
                f'?before-id={last.id}'
                f'&before-created-at={last.created_at.isoformat().replace("+00:00", "Z")}'
            )

        return Response({
            'count': AuditLogs.objects.count(),
            'next': next_url,
            'previous': None,
            'results': serializer.data,
        })
