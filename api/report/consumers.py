from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_reports(user):
    from api.report.services import ReportService
    from api.report.serializers import ReportSerializer
    from django.conf import settings

    reports = list(ReportService.get_all(technician_id=user.id)[:16])

    has_more = len(reports) > 15
    reports = reports[:15]

    oldest_report = reports[-1] if reports else None

    return {
        'data': ReportSerializer(reports, many=True).data,
        'next': (
            f'{settings.API_BASE_URL}/api/reports/'
            f'&before-id={oldest_report.id}'
            f'?before-created-at='
            f'{oldest_report.created_at.isoformat().replace("+00:00", "Z")}'
            if has_more and oldest_report
            else None
        )
    }


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
            'report': reports['data'],
            'next': reports['next']
        }))

    async def disconnect(self, close_code):
        from api.user.models import User

        user = self.scope['user']

        if user.is_anonymous:
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
        
