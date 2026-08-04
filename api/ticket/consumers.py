from channels.generic.websocket import AsyncWebsocketConsumer
import json


class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            'tickets',
            self.channel_name
        )

        await self.accept()

        from api.ticket.services import TicketService
        tickets = TicketService.get_all(user)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_tickets',
            'tickets': tickets
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            'tickets',
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