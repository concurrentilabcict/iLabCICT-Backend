
from api.notification.models import Notification
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format
from api.user.models import User
from django.db.models import Q
class NotificationService():

    @staticmethod
    def get_all(user=None,
                type=None,
                status=None,
                date=None):
        
        NotificationService.validate_filters(
            type=type,
            status=status,
            date=date
        )

        queryset = Notification.objects.select_related('ticket')

        if user is not None:
            queryset = queryset.filter(
                 Q(receiver_role=user.role) &
                    (
                        Q(receiver_id=user.id) |
                        Q(receiver_id__isnull=True)
                    ))

        if type is not None: 
            queryset = queryset.filter(type=type)
        
        if status is not None:
            queryset = queryset.filter(status=status)

        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        if user is None:
            queryset = []
            
        return queryset
    
    @staticmethod
    def validate_filters(type,status,date):
        allowed_notification_type = Notification.NotificationTypes.values
        allowed_notification_status = Notification.NotificationStatus.values

        if type and type not in allowed_notification_type:
            raise ValidationError('Invalid notification type')
        
        if status and status not in allowed_notification_status:
            raise ValidationError('Invalid notification status')
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')


    
    @staticmethod
    def create_new_ticket_notification(receiver_id, title, ticket_id):

        if receiver_id is None:
            Notification.objects.create(
                receiver = None,
                receiver_role=User.UserRole.TECHNICIAN, 
                title = title,
                ticket_id = ticket_id,
                report = None,
                type = Notification.NotificationTypes.TICKET,
                status = Notification.NotificationStatus.UNREAD
            )
        else:
            Notification.objects.create(
                receiver = receiver_id,
                receiver_role=User.UserRole.TECHNICIAN, 
                title = title,
                ticket_id = ticket_id,
                report = None,
                type = Notification.NotificationTypes.TICKET,
                status = Notification.NotificationStatus.UNREAD
            )

    @staticmethod
    def update_ticket_receiver(receiver_id, notif_id):
        Notification.objects.filter(id=notif_id).update(receiver_id=receiver_id)


    @staticmethod
    def create_new_report_notification(receiver_id, title, report_id):
        
        if receiver_id is None:
            Notification.objects.create(
                receiver = None,
                receiver_role=User.UserRole.ADMIN,
                title = title,
                report_id = report_id,
                ticket = None,
                type = Notification.NotificationTypes.REPORT,
                status = Notification.NotificationStatus.UNREAD
            )
        else:
            Notification.objects.create(
                receiver = receiver_id,
                receiver_role=User.UserRole.ADMIN,
                title = title,
                report_id = report_id,
                ticket = None,
                type = Notification.NotificationTypes.REPORT,
                status = Notification.NotificationStatus.UNREAD
            )
    
    
