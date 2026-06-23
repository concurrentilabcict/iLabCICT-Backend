
from api.notification.models import Notification

class NotificationService():

    @staticmethod
    def get_all_notification_per_user(user_id=None):
        queryset = Notification.objects.filter(receiver_id=user_id)
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
    
    
