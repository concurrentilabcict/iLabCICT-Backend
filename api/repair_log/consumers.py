from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_repair_logs(user):
    from api.repair_log.services import RepairLogService
    from api.repair_log.serializers import MainRepairLogReadSerializer
    from django.conf import settings

    repair_logs, next_cursor = RepairLogService.get_paginated_repair_logs(user=user)

    return {
        'data': MainRepairLogReadSerializer(repair_logs, many=True).data,
        'next': (
            f'{settings.API_BASE_URL}'
            f'/api/repair-logs/'
            f'?cursor={next_cursor}'
            if next_cursor
            else None
        )
    }

class RepairLogConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from api.user.models import User

        user = self.scope['user']

        allowed_roles = {
            User.UserRole.TECHNICIAN,
            User.UserRole.ADMIN
        }

        if user.is_anonymous:
            await self.close(code=4001)
            return

        if user.role not in allowed_roles:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            f'repair_logs_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_add(
                'repair_logs_admin',
                self.channel_name
            )

        await self.accept()

        repair_logs = await get_initial_repair_logs(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_repair_logs',
            'repair_logs': repair_logs['data'],
            'next': repair_logs['next']        
        }))

    async def disconnect(self, close_code):
        from api.user.models import User

        user = self.scope['user']
        
        if user.is_anonymous:
            return

        await self.channel_layer.group_discard(
            f'repair_logs_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_discard(
                f'repair_logs_admin',
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

    async def repair_log_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'repair_log_created',
            'repair_log': event['repair_log']
        }))