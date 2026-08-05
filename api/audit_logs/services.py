
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