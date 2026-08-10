from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_room():
    from api.room.services import RoomService
    from api.room.serializers import RoomReadSerializer

    queryset = RoomService.get_all()

    return RoomReadSerializer(queryset, many=True).data

@database_sync_to_async
def get_initial_room_computers(room_id):
    from api.room.services import RoomService
    from api.room.serializers import RoomAndComputerListSerializer
    room = RoomService.get_computers_room_id(room_id=room_id)

    computers = room.initial_computers

    last_computer = computers[-1] if computers else None

    return{
        'room_with_computers': RoomAndComputerListSerializer(room).data,
        'next_after_id': (
            last_computer.id
            if last_computer
            else None
        ) 
    }
    

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
    async def connect(self):
        user = self.scope['user']

        if user.is_anonymous:
                    await self.close(code=4001)
                    return

        try:
            room_id = int(
                self.scope['url_route']['kwargs']['room_id']
            )
        except (KeyError, ValueError, TypeError):
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            f'room_{room_id}',
            self.channel_name
        )

        await self.accept()

        room_computers_data = await get_initial_room_computers(
            room_id=room_id,
        )

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_room_computers',
            'initial_computers': (room_computers_data['room_with_computers']),
            'next_after_id': (room_computers_data['next_after_id'])
        }))


    async def disconnect(self, code):
        user = self.scope['user'] 

        if user.is_anonymous:
            return

        room_id = int(
            self.scope['url_route']['kwargs']['room_id']
                )

        await self.channel_layer.group_discard(
            f'room_{room_id}',
            self.channel_name
        )        

    async def computer_created(self, event):
        await self.send(text_data=json.dumps({
            'event': 'computer_created',
            'computer': event['computer']
        }))

    async def computer_updated(self, event):
        await self.send(text_data=json.dumps({
            'event': 'computer_updated',
            'computer': event['computer']
        }))