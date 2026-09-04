
from api.notification.models import Notification
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format
from api.user.models import User
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from api.notification.serializers import NotificationSerializer
from api.cursor import CursorService

from api.user_push_token.services import UserPushTokenService
class NotificationService():

    PAGE_SIZE=30

    @staticmethod
    def get_paginated_notifications(user, cursor=None,status=None):
        queryset = NotificationService.get_all(user=user,status=status)

        if cursor:
            cursor_data = CursorService.decode_cursor(cursor=cursor)

            if cursor_data is None:
                raise ValueError('Invalid cursor')

            created_at = cursor_data['created_at']
            notif_id = cursor_data['id']

            queryset = queryset.filter(
                Q(created_at__lt=created_at) |
                Q(
                    created_at=created_at,
                    id__lt=notif_id
                )
            )

        queryset = queryset.order_by(
            '-created_at',
            '-id'
        )

        notifications = list(
            queryset[:NotificationService.PAGE_SIZE + 1]
        )

        has_more = len(notifications) > NotificationService.PAGE_SIZE

        notifications = notifications[:NotificationService.PAGE_SIZE]

        next_cursor = None

        if has_more and notifications:
            next_cursor = CursorService.encode_cursor(
                notifications[-1]
            )

        return notifications, next_cursor



    @staticmethod
    def get_all(user=None,
                status=None,
                ):
        
        NotificationService.validate_filters(
            status=status,
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

        if status is not None:
            queryset = queryset.filter(status=status)

        if user is None:
            queryset = queryset.none()
            
        return queryset
    
    @staticmethod
    def validate_filters(status):
        allowed_notification_status = Notification.NotificationStatus.values

        if status and status not in allowed_notification_status:
            raise ValidationError('Invalid notification status')
        
        
    @staticmethod
    def create_new_ticket_notification(recipient, title, entity, role, event, body=None):
        notification = None
        channel_layer = get_channel_layer()

        if role == User.UserRole.FACULTY:
            notification = Notification.objects.create(
                recipient_id_id=recipient.id,
                entity_id=entity.id,
                entity_type = Notification.NotificationEntityTypes.TICKET,
                event_type = event,
                title=title,
                activity_summary={
                    'actor': entity.assigned_to.get_full_name(),
                    'entity_title': entity.title,
                    'message': body  
                },
                status=Notification.NotificationStatus.UNREAD
                        )

        elif role == User.UserRole.TECHNICIAN:
            notification = Notification.objects.create(
                recipient_id_id=recipient.id if recipient is not None else None,
                entity_id=entity.id,
                entity_type = Notification.NotificationEntityTypes.TICKET,
                event_type = event,
                title=title,
                activity_summary={
                    'actor': entity.reported_by.get_full_name(),
                    'entity_title': entity.title,
                    'message': body  
                },
                status=Notification.NotificationStatus.UNREAD
                        )

        if recipient is None:
            technicians = User.objects.filter(role='technician')
            UserPushTokenService.send_notification_to_users(
                users=technicians,
                title=title,
                body=body,
                extra_data={'ticket_id': entity.id}
            )
        else:
            UserPushTokenService.send_notification_to_users(
                users=recipient,
                title=title,
                body=body,
                extra_data={'ticket_id': entity.id}
            )

        NotificationService.send_notification_ticket_channels(
            recipient_id=recipient.id if recipient is not None else None,
            role=role,
            data=NotificationSerializer(notification).data,
            channel_layer=channel_layer
        )


    @staticmethod
    def send_notification_ticket_channels(recipient_id, role, data, channel_layer):

        if recipient_id is not None:
            async_to_sync(channel_layer.group_send)(
                f'notification_user_{recipient_id}',
                {
                    'type': 'notification_created',
                    'notification': data,
                }
            )

        elif role == User.UserRole.TECHNICIAN:
            async_to_sync(channel_layer.group_send)(
                'notification_technicians',
                {
                    'type': 'notification_created',
                    'notification': data,
                }
            )

        async_to_sync(channel_layer.group_send)(
            'notification_admins',
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
            'notification_technicians',
            {
                'type': 'notification_archived',
                'notification_id': notification.id,
            }
        )
        

    @staticmethod
    def create_new_report_notification(recipient, title, entity, body=None):
        channel_layer = get_channel_layer()

        notification = Notification.objects.create(
            recipient_id=recipient.id if recipient is not None else None,
            entity_id=entity.id,
            entity_type = Notification.NotificationEntityTypes.WEEKLY_REPORT,
            event_type = Notification.NotificationEventTypes.UNICAST_TECHNICIAN,
            title=title,
            activity_summary={
                'actor': entity.technician.get_full_name(),
                'entity_title': entity.title,
                'message': body
            },
            status=Notification.NotificationStatus.UNREAD
            )

        UserPushTokenService.send_notification_to_users(
            users=recipient.id if recipient is not None else None,
            title=title,
            body=body,
            extra_data={'report_id': entity.id}
        )

        async_to_sync(channel_layer.group_send)(
            f'notification_user_{recipient.id if recipient is not None else None}',
            {
                'type': 'notification_created',
                'notification_id': NotificationSerializer(notification).data,
            }
        )

        async_to_sync(channel_layer.group_send)(
            'notification_admin',
            {
                'type': 'notification_created',
                'notification_id': NotificationSerializer(notification).data,
            }
        )
        
        
    
    
