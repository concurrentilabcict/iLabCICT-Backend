
from api.audit_logs.models import AuditLogs
from api.user.models import User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync 
from api.audit_logs.serializers import AuditLogsSerializer
class AuditLogsService():

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
        queryset = AuditLogs.objects.select_related('audit_logs')

        if user is None:
            return queryset.none()

        if user.role == User.UserRole.ADMIN:
            return queryset.order_by('-created_at', '-id')

        return queryset.none()

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