
from api.notification.models import Notification
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format
from api.user.models import User
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from api.notification.serializers import NotificationSerializer
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

        queryset = queryset.exclude(status=Notification.NotificationStatus.ARCHIVED)
        
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

        notification = None
        channel_layer = get_channel_layer()

        if role == User.UserRole.FACULTY:
            notification = Notification.objects.create(
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
            notification = Notification.objects.create(
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

        NotificationService.send_notification_ticket_channels(
            recipient_id=recipient_id,
            role=role,
            data=NotificationSerializer(notification).data,
            channel_layer=channel_layer
        )


    @staticmethod
    def send_notification_ticket_channels(recipient_id, role, data, channel_layer):

        if recipient_id is not None:
            async_to_sync(channel_layer.group_send)(
                f'user_{recipient_id}',
                {
                    'type': 'notification_created',
                    'notification': data,
                }
            )

        elif role == User.UserRole.TECHNICIAN:
            async_to_sync(channel_layer.group_send)(
                'technicians',
                {
                    'type': 'notification_created',
                    'notification': data,
                }
            )

        async_to_sync(channel_layer.group_send)(
            'admins',
            {
                'type': 'notification_created',
                'notification': data
            }
        )
        
    @staticmethod
    def update_ticket_technician_recipient(entity_id):
        channel_layer = get_channel_layer()

        notification = Notification.objects.filter(
            entity_id=entity_id,
            entity_type=Notification.NotificationEntityTypes.TICKET,
            recipient_id=None
        ).first()

        if notification is None:
            return

        notification.status = Notification.NotificationStatus.ARCHIVED
        notification.save(update_fields=["status"])

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'notification_archived',
                'notification_id': notification.id,
            }
        )
        

    @staticmethod
    def create_new_report_notification(recipient_id, title, entity):
        channel_layer = get_channel_layer()
        

        notification = Notification.objects.create(
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

        async_to_sync(channel_layer.group_send)(
            f'user_{recipient_id}',
            {
                'type': 'notification_created',
                'notification_id': NotificationSerializer(notification).data,
            }
        )

        async_to_sync(channel_layer.group_send)(
            'admin',
            {
                'type': 'notification_created',
                'notification_id': NotificationSerializer(notification).data,
            }
        )
        
        
    
    
