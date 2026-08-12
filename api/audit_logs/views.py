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
from urllib.parse import urlencode
class AuditLogsListView(ListAPIView):
    serializer_class = AuditLogsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        cursor = self.request.query_params.get('cursor')
        query_search = self.request.query_params.get('q')

        try:
            logs, next_cursor = (
                AuditLogsService.get_paginated_audit_logs(
                    user=request.user,
                    cursor=cursor,
                    query_search=query_search
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        next_url = None

        if next_cursor:
            params = {
                'cursor': next_cursor
            }

            if query_search:
                params['q'] = query_search

            next_url = (
                f'{settings.API_BASE_URL}'
                f'/api/audit-logs/'
                f'?{urlencode(params)}'
            )

        return Response({
            'results': AuditLogsSerializer(logs, many=True).data,
            'next': next_url
        })

