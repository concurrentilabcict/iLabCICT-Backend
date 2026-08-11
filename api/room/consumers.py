from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

@database_sync_to_async
def get_initial_room(include=''):
    from api.room.services import RoomService
    from api.room.serializers import RoomReadSerializer
    from django.conf import settings

    rooms, next_cursor = RoomService.get_paginated_rooms(include=include)

    next_url = None

    if next_cursor:
        next_url = f'{settings.API_BASE_URL}/api/rooms/?cursor={next_cursor}'

        if 'computers' in include.split(','):
            next_url += '&include=computers'

    return{
        'data': RoomReadSerializer(rooms, many=True, context={'include': include}).data,
        'next': next_url
    }

@database_sync_to_async
def get_initial_room_computers(room_id):
    from api.room.services import RoomService
    from api.room.serializers import RoomAndComputerListSerializer
    from django.conf import settings

    room, next_cursor = RoomService.get_computers_room_id(room_id=room_id)
    
    return{
        'room_with_computers': RoomAndComputerListSerializer(
            room,
        ).data,

        'next': (
            f'{settings.API_BASE_URL}/api/rooms/'
            f'{room_id}/computers/'
            f'?cursor={next_cursor}'
            if next_cursor 
            else None
        )
    }
    
class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from urllib.parse import parse_qs

        user = self.scope['user']

        query_string = self.scope["query_string"].decode()
        query_params = parse_qs(query_string)

        include = query_params.get("include", [""])[0]
       
        if user.is_anonymous:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            'rooms_all',
            self.channel_name
        )

        await self.accept()

        rooms = await get_initial_room(include=include)

        await self.send(text_data=json.dumps({
            'message': 'connected'
        }))

        await self.send(text_data=json.dumps({
            'event': 'initial_rooms',
            'room': rooms['data'],
            'next': rooms['next']
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
            'next_after_id': (room_computers_data['next'])
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