from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_notifications(user):
    from api.notification.services import NotificationService
    from api.notification.serializers import NotificationSerializer
    from django.conf import settings

    notifications, next_cursor = NotificationService.get_paginated_notifications(user=user)

    return {
        'data': NotificationSerializer(notifications, many=True).data,
        'next': (
            f'{settings.API_BASE_URL}'
            f'/api/notifications/user/'
            f'?cursor={next_cursor}'
            if next_cursor
            else None
        )
    }

class NotifcationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        from api.user.models import User
        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            f'notification_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_add(
                'notification_admins',
                self.channel_name
            )

        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_add(
                'notification_technicians',
                self.channel_name
            )

        await self.accept()

        notifications = await get_initial_notifications(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_notifications',
            'notification': notifications['data'],
            'next':notifications['next']
        }))



    async def disconnect(self, close_code):
        from api.user.models import User
        user = self.scope['user']

        if user.is_anonymous:
            return
        
        await self.channel_layer.group_discard(
            f'notification_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_discard(
                'notification_admins',
                self.channel_name
            )

        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_discard(
                'notification_technicians',
                self.channel_name
            )

    async def notification_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'notification_created',
            'notification': event['notification']
        }))

    async def notification_updated(self, event):
        await self.send(text_data=json.dumps({
            'event': 'notification_updated',
            'notification': event['notification']
        }))

    async def notification_archived(self, event):
        await self.send(text_data=json.dumps({
            'event': 'notification_archived',
            'notification': event['notification_id']
        }))