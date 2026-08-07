from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_tickets(user):
    from api.ticket.services import TicketService
    from api.ticket.serializers import TicketReadSerializer

    queryset = TicketService.get_all(user=user)

    return TicketReadSerializer(queryset, many=True).data

class TicketConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from api.user.models import User

        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            f'tickets_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_add(
                'tickets_admin',
                self.channel_name
            )

        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_add(
                'tickets_technicians',
                self.channel_name
            )

        await self.accept()

        tickets = await get_initial_tickets(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_tickets',
            'ticket': tickets
        }))

    async def disconnect(self, close_code):
        from api.user.models import User
        user = self.scope['user']

        if user.is_anonymous:
            return

        await self.channel_layer.group_discard(
            f'tickets_user_{user.id}',
            self.channel_name
        )

        if user.role == User.UserRole.ADMIN:
            await self.channel_layer.group_discard(
                'tickets_admin',
                self.channel_name
            )
        
        elif user.role == User.UserRole.TECHNICIAN:
            await self.channel_layer.group_discard(
                'tickets_technicians',
                self.channel_name
            )
        

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

    async def ticket_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'ticket_created',
            'ticket': event['ticket']
        }))
    
    async def ticket_updated(self, event):
        await self.send(text_data=json.dumps({
            'event': 'ticket_updated',
            'ticket': event['ticket']
        }))

    async def ticket_deleted(self, event):
        await self.send(text_data=json.dumps({
            'event': 'ticket_deleted',
            'ticket': event['ticket_id']
        }))

    async def ticket_reassigned(self, event):
        await self.send(text_data=json.dumps({
            'event': 'ticket_reassigned',
            'ticket': event['ticket']
        }))