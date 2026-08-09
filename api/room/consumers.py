from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_room():
    from api.room.services import RoomService
    from api.room.serializers import RoomReadSerializer

    queryset = RoomService.get_all()

    return RoomReadSerializer(queryset, many=True).data

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        user = self.scope['user']

        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            'rooms_all',
            self.channel_name
        )

        await self.accept()

        rooms = await get_initial_room()

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_rooms',
            'room': rooms
        }))

    async def disconnect(self, close_code):
        user = self.scope['user']

        if user.is_anonymous:
            return

        await self.channel_layer.group_discard(
            'rooms_all',
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

    async def room_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'room_created',
            'room': event['room']
        }))

    async def room_updated(self, event):
        await self.send(text_data=json.dumps({
            'event': 'room_updated',
            'room': event['room']
        }))


class RoomIDAllComputersConsumer(AsyncWebsocketConsumer):
    ...

    