from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from api.user.models import User

class NotifcationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):

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

        

        await self.send(text_data=json.dumps({
            'message': 'connected'
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