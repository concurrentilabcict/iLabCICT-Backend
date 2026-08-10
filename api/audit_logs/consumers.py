from channels.generic.websocket import AsyncWebsocketConsumer
import json 
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_audit_logs(user):
    from api.audit_logs.services import AuditLogsService
    from api.audit_logs.serializers import AuditLogsSerializer
    from django.conf import settings

    logs = list(AuditLogsService.get_all(user=user)[:51])

    has_more = len(logs) > 50
    logs = logs[:50]

    oldest_log = logs[-1] if logs else None

    return {
        'data':  AuditLogsSerializer(logs, many=True).data,
        'next': (
            f'{settings.API_BASE_URL}/api/audit-logs/'
            f'&before-id={oldest_log.id}'
            f'?before-created-at='
            f'{oldest_log.created_at.isoformat().replace("+00:00", "Z")}'
            if has_more and oldest_log
            else None
        )
    } 

class AuditLogsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from api.user.models import User

        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        if user.role != User.UserRole.ADMIN:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            f'audit_logs_admin',
            self.channel_name
        )

        await self.accept()

        audit_logs = await get_initial_audit_logs(user=user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_audit_logs',
            'audit_log': audit_logs['data'],
            'next': audit_logs['next']
        }))

    async def disconnect(self, close_code):

        user = self.scope['user']

        if user.is_anonymous:
            return

        await self.channel_layer.group_discard(
            'audit_logs_admin',
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return  

    async def audit_log_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'audit_log_created',
            'audit_log': event['audit_log']
        }))

    