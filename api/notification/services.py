
from api.notification.models import Notification
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format

class NotificationService():

    @staticmethod
    def get_all(user_id=None,
                type=None,
                status=None,
                date=None):
        
        NotificationService.validate_filters(
            user_id=user_id,
            type=type,
            status=status,
            date=date
        )

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
    def validate_filters(user_id,type,status,date):
        allowed_notification_type = Notification.NotificationTypes.values
        allowed_notification_status = Notification.NotificationStatus.values

        if user_id is not None:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                raise ValidationError({
                    "message": "Invalid user-id."
                })
        
        if type and type not in allowed_notification_type:
            raise ValidationError({
                'message': f'Invalid notification type' 
            })
        
        if status and status not in allowed_notification_status:
            raise ValidationError({
                'message': f'Invalid notification status'
            })
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError({
                'message': f'Date format must be in YYYY-MM-DD'
            })


    
    @staticmethod
    def create_new_ticket_notification(receiver_id, title, ticket_id):

        Notification.objects.create(
            receiver = receiver_id,
            title = title,
            ticket_id = ticket_id,
            report = None,
            type = Notification.NotificationTypes.TICKET,
            status = Notification.NotificationStatus.UNREAD
        )

    @staticmethod
    def create_new_report_notification(receiver_id, title, report_id):
        
        Notification.objects.create(
            receiver = receiver_id,
            title = title,
            report_id = report_id,
            ticket = None,
            type = Notification.NotificationTypes.REPORT,
            status = Notification.NotificationStatus.UNREAD
        )
    
    
