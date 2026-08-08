from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_reports(user):
    from api.report.services import ReportService
    from api.report.serializers import ReportSerializer

    queryset = ReportService.get_all(technician_id=user.id)

    return ReportSerializer(queryset, many=True).data

class ReportConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from api.user.models import User

        allowed_roles = {
            User.UserRole.TECHNICIAN,
            User.UserRole.ADMIN
        }

        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        if user.role not in allowed_roles:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            f'reports_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_add(
                'reports_admin',
                self.channel_name
            )

        await self.accept()

        reports = await get_initial_reports(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_reports',
            'report': reports
        }))

    async def disconnect(self, close_code):
        from api.user.models import User

        user = self.scope['user']

        if user.is_anonymous:
            return

        if user.role == User.UserRole.FACULTY:
            return

        await self.channel_layer.group_discard(
            f'reports_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_discard(
                f'reports_admin',
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

    async def report_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'report_created',
            'report': event['report']
        }))   
        
