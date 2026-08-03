
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
            status=status,
            date=date
        )

        queryset = Notification.objects.select_related('recipient_id')

        if user.role == User.UserRole.FACULTY:
            queryset = queryset.filter(
                Q(
                    event_type=Notification.NotificationEventTypes.UNICAST_FACULTY,
                    recipient_id=user.id,
                )
                |
                Q(
                    event_type=Notification.NotificationEventTypes.MULTICAST_FACULTY,
                )
            )

        elif user.role == User.UserRole.TECHNICIAN:
            queryset = queryset.filter(
                Q(
                    event_type=Notification.NotificationEventTypes.UNICAST_TECHNICIAN,
                    recipient_id=user.id,
                )
                |
                Q(
                    event_type=Notification.NotificationEventTypes.MULTICAST_TECHNICIAN,
                )
            )


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
    def validate_filters(status,date):
        allowed_notification_status = Notification.NotificationStatus.values

        if status and status not in allowed_notification_status:
            raise ValidationError('Invalid notification status')
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')
    
    @staticmethod
    def create_new_ticket_notification(recipient_id, title, entity, role, event):

        if role == User.UserRole.FACULTY:
            Notification.objects.create(
                recipient_id=recipient_id,
                entity_id=entity.id,
                entity_type = Notification.NotificationEntityTypes.TICKET,
                event_type = event,
                title=title,
                activity_summary={
                    'actor': entity.assigned_to.get_full_name(),
                    'entity_title': entity.title  
                },
                status=Notification.NotificationStatus.UNREAD
                        )
 
        elif role == User.UserRole.TECHNICIAN:
            Notification.objects.create(
                recipient_id=recipient_id,
                entity_id=entity.id,
                entity_type = Notification.NotificationEntityTypes.TICKET,
                event_type = event,
                title=title,
                activity_summary={
                    'actor': entity.reported_by.get_full_name(),
                    'entity_title': entity.title  
                },
                status=Notification.NotificationStatus.UNREAD
                        )

    @staticmethod
    def update_ticket_technician_recipient(recipient_id, entity_id):
        Notification.objects.filter(
            entity_id = entity_id,
            entity_type = Notification.NotificationEntityTypes.TICKET,
            recipient_id = None
        ).update(
            recipient_id = recipient_id,
            event_type = Notification.NotificationEventTypes.UNICAST_TECHNICIAN
            )
        

    @staticmethod
    def create_new_report_notification(recipient_id, title, entity):
        Notification.objects.create(
            recipient_id=recipient_id,
            entity_id=entity.id,
            entity_type = Notification.NotificationEntityTypes.WEEKLY_REPORT,
            event_type = Notification.NotificationEventTypes.UNICAST_TECHNICIAN,
            title=title,
            activity_summary={
                'actor': entity.technician.get_full_name(),
                'entity_title': entity.title  
            },
            status=Notification.NotificationStatus.UNREAD
            )
        
        
    
    
