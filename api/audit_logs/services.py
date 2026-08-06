
from api.audit_logs.models import AuditLogs

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

        AuditLogs.objects.create(
            performed_by=performed_by,
            action_title=action_title,
            action_summary=action_summary,
            metadata=metadata,
        )