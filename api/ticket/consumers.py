from channels.generic.websocket import AsyncWebsocketConsumer
import json

class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        await self.channel_layer.group_add(
            'technicians',
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            'technicians',
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