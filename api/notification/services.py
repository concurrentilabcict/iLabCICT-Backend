
from api.notification.models import Notification

class NotificationService():

    @staticmethod
    def get_all(user_id=None,
                type=None,
                status=None,
                date=None):
        
        queryset = Notification.objects.all()

        if user_id is not None:
            queryset = queryset.filter(receiver_id=user_id)

        if type is not None: 
            queryset = queryset.filter(type=type)
        
        if status is not None:
            queryset = queryset.filter(status=status)

        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        if user_id is None:
            queryset = []
            
        return queryset
    
    @staticmethod
    def create_new_ticket_notification(receiver_id, title, ticket_id):

        Notification.objects.create(
            receiver = receiver_id,
            title = title,
            ticket_id = ticket_id,
            report = None,
            type = 'ticket',
            status = 'unread'
        )

    @staticmethod
    def create_new_report_notification(receiver_id, title, report_id):
        
        Notification.objects.create(
            receiver = receiver_id,
            title = title,
            report_id = report_id,
            ticket = None,
            type = 'report',
            status = 'unread'
        )
    
    
