from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_notifications(user):
    from api.notification.services import NotificationService
    from api.notification.serializers import NotificationSerializer

    queryset = NotificationService.get_all(user=user)

    return NotificationSerializer(queryset, many=True).data

class NotifcationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        from api.user.models import User
        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            f'user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_add(
                'admins',
                self.channel_name
            )

        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_add(
                'technicians',
                self.channel_name
            )

        await self.accept()

        notifications = await get_initial_notifications(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_notifications',
            'notification': notifications
        }))



    async def disconnect(self, close_code):

        user = self.scope['user']

        if user.is_anonymous:
            return
        
        await self.channel_layer.group_discard(
            f'user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_discard(
                'admins',
                self.channel_name
            )

        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_discard(
                'technicians',
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