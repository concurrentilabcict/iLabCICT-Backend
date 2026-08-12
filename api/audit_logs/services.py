
from api.audit_logs.models import AuditLogs
from api.user.models import User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync 
from api.cursor import CursorService
from django.db.models import Q
class AuditLogsService():

    PAGE_SIZE = 50

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip

    @staticmethod
    def get_user_agent(request):
        return request.META.get('HTTP_USER_AGENT')

    @staticmethod
    def log(
        *,
        request,
        performed_by,
        action_title,
        action_summary,
        metadata=None,
            ):
        from api.audit_logs.serializers import AuditLogsSerializer

        metadata = metadata or {}

        metadata.setdefault(
            "ip_address",
            AuditLogsService.get_client_ip(request)
        )
        metadata.setdefault(
            "user_agent",
            AuditLogsService.get_user_agent(request)
        )

        audit_log = AuditLogs.objects.create(
            performed_by=performed_by,
            action_title=action_title,
            action_summary=action_summary,
            metadata=metadata,
        )

        AuditLogsService.broadcast_audit_log_event(
            audit_log=AuditLogsSerializer(audit_log).data
        )

    @staticmethod
    def get_all(user=None):
        queryset = AuditLogs.objects.select_related('performed_by')

        if user is None:
            return queryset.none()

        if user.role == User.UserRole.ADMIN:
            return queryset.order_by('-created_at', '-id')

        return queryset.none()

    @staticmethod
    def get_paginated_audit_logs(user, cursor=None, query_search=None):
        queryset = AuditLogsService.get_all(user=user)

        if query_search:
            queryset = AuditLogsService.search_audit_logs(
                queryset=queryset,
                query_search=query_search
            )
        if cursor:
            cursor_data = CursorService.decode_cursor(cursor=cursor)

            if cursor_data is None:
                raise ValueError('Invalid cursor')

            created_at = cursor_data['created_at']
            logs_id = cursor_data['id']

            queryset = queryset.filter(
                Q(created_at__lt=created_at) |
                Q(
                    created_at=created_at,
                    id__lt=logs_id
                )
            )

        queryset = queryset.order_by(
            '-created_at',
            '-id'
        )

        logs = list(
            queryset[:AuditLogsService.PAGE_SIZE + 1]
        )

        has_more = len(logs) > AuditLogsService.PAGE_SIZE

        logs = logs[:AuditLogsService.PAGE_SIZE]

        next_cursor = None

        if has_more and logs:
            next_cursor = CursorService.encode_cursor(
                logs[-1]
            )

        return logs, next_cursor

    @staticmethod
    def broadcast_audit_log_event(audit_log):
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'audit_logs_admin',
            {
                'type': 'audit_log_created',
                'audit_log': audit_log
            }
        )

    @staticmethod
    def search_audit_logs(query_search, queryset):
        terms = query_search.strip().split()

        for term in terms:
            queryset = queryset.filter(
                Q(action_title__icontains=term) |
                Q(action_summary__icontains=term) |
                Q(created_at__date__icontains=term) |
                Q(performed_by__first_name__icontains=term) |
                Q(performed_by__last_name__icontains=term) |
                Q(metadata__ip_address__icontains=term) |
                Q(metadata__user_agent__icontains=term) 
            )

        return queryset