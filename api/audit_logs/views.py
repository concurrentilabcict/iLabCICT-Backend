from rest_framework.generics import ListAPIView
from api.audit_logs.serializers import AuditLogsSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated
from api.audit_logs.services import AuditLogsService
from django.utils.dateparse import parse_datetime
from api.audit_logs.models import AuditLogs
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings

class AuditLogsListView(ListAPIView):
    serializer_class = AuditLogsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        cursor = self.request.query_params.get('cursor')

        try:
            logs, next_cursor = (
                AuditLogsService.get_paginated_audit_logs(
                    user=request.user,
                    cursor=cursor
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        return Response({
            'results': AuditLogsSerializer(logs, many=True).data,
            'next': (
                f'{settings.API_BASE_URL}'
                f'/api/audit-logs/'
                f'?cursor={next_cursor}'
                if next_cursor
                else None
            )
        })

