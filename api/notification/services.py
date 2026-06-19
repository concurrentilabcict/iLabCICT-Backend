
from api.notification.models import Notification

class NotificationService():

    @staticmethod
    def get_all_notification_per_user(user_id=None):
        queryset = Notification.objects.filter(receiver_id=user_id)
        return queryset
    
    @staticmethod
    def create_new_ticket_notification(receiver_id, title, header, type):
        Notification.objects.create(
            receiver = receiver_id,
            title = title,
            header = header,
            ticket_type = type,
            status = 'unread'
        )
    
    
    
