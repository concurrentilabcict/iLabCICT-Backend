from api.room.models import Room
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Q, Prefetch
from api.computer.models import Computer
from api.ticket.models import Ticket
from api.audit_logs.services import AuditLogsService 
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.room.serializers import RoomReadSerializer
from api.cursor import SingleCursorService
class RoomService:

    PAGE_SIZE=15

    @staticmethod
    def get_paginated_rooms(cursor=None, include= ""):
        queryset = (Room.objects
            .select_related('assigned_custodian')
            .annotate(computer_count=Count('computers', distinct=True),
                        computer_count_with_active_issues=Count(
                        'computers',
                        filter=Q(computers__tickets__status=Ticket.TicketStatus.ONGOING),
                        distinct=True
                        ))
            .order_by('id')
            )

        if "computers" in include.split(","):
            queryset = queryset.prefetch_related("computers")

        if cursor:
            cursor_data = SingleCursorService.decode_cursor(cursor=cursor)

            if cursor_data is None:
                raise ValueError('Invalid cursor.')

            room_id = cursor_data['id']

            queryset = queryset.filter(
                id__gt=room_id
            )

        rooms = list(
            queryset[:RoomService.PAGE_SIZE + 1]
        )

        has_more = len(rooms) > RoomService.PAGE_SIZE

        rooms = rooms[:RoomService.PAGE_SIZE]

        next_cursor = None
        if has_more and rooms:
            next_cursor = SingleCursorService.encode_cursor(
                rooms[-1]
            )

        return rooms, next_cursor

    @staticmethod
    def get_computers_room_id(room_id=None, cursor=None):

        computers_queryset = (
                    Computer.objects
                    .filter(room_id=room_id)
                    .order_by('id')
                )
        
        if cursor:
            cursor_data = SingleCursorService.decode_cursor(cursor=cursor)

            if cursor_data is None:
                raise ValueError('Invalid cursor.')

            after_id = cursor_data['id']

            computers_queryset = Computer.objects.filter(
                room_id=room_id,
                id__gt=after_id
            ).order_by('id')

        computers_queryset = computers_queryset[:RoomService.PAGE_SIZE + 1]

        queryset = (Room.objects
                    .select_related('assigned_custodian')
                    .prefetch_related(
                        Prefetch(
                            'computers',
                            queryset=computers_queryset,
                            to_attr='initial_computers'
                        ) 
                    )
                    .annotate(total_computer=Count('computers'))
                    .filter(id=room_id))

        room = queryset.first()

        if room is None:
            return None, None

        computers = room.initial_computers
        has_more = len(computers) > RoomService.PAGE_SIZE
        computers = computers[:RoomService.PAGE_SIZE]

        room.initial_computers = computers

        next_cursor = None

        if has_more and computers:
            next_cursor = SingleCursorService.encode_cursor(
                computers[-1]
            )

        return room, next_cursor


    @staticmethod
    def get_all(status=None,
                building=None,
                room=None,
                include=""):
        
        RoomService.validate_filters(
            status=status,
            building=building,
            room=room
            )

        queryset = (Room.objects
                    .select_related('assigned_custodian')
                    .annotate(computer_count=Count('computers', distinct=True),
                              computer_count_with_active_issues=Count(
                                'computers',
                                filter=Q(computers__tickets__status=Ticket.TicketStatus.ONGOING),
                                distinct=True
                              ))
                    )
        
        if "computers" in include.split(","):
            queryset = queryset.prefetch_related("computers")

        if status is not None:
            queryset = queryset.filter(status=status)
        
        if building is not None: 
            queryset = queryset.filter(building_name=building)
        
        if room is not None:
            queryset = queryset.filter(room_name=room)

        return queryset
    
    @staticmethod
    def validate_filters(status,building,room):
        allowed_room_statuses = Room.RoomStatus.values
        allowed_building_names = Room.BuildingName.values

        if status and status not in allowed_room_statuses:
            raise ValidationError('Invalid room status')
        
        if building and building not in allowed_building_names:
            raise ValidationError('Invalid building name')
        
        if isinstance(room, bool):
            raise ValidationError('Invalid room name')

    @staticmethod
    def log_room_create(room, request):
        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='Room created',
            action_summary=f"{request.user.get_full_name()} created room '{room.room_name}'.",
            metadata={
                'room_id': room.id,
                'room_name': room.room_name,
                'assigned_technician_id': room.assigned_technician_id
            }
        )

    @staticmethod
    def create_room(serializer, request):
        room = serializer.save()

        RoomService.broacast_room_event(
            room=RoomReadSerializer(room).data,
            event_type='room_created'
        )

        RoomService.log_room_create(
            room=room,
            request=request
        )

        return room

    @staticmethod
    def log_room_update(room,
                        request,
                        changes):
        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='Room updated',
            action_summary=f"{request.user.get_full_name()} updated room '{room.room_name}'.",
            metadata={
                'room_id': room.id,
                'changes': changes
                }
       )

    @staticmethod
    def update_room(serializer, request):
        room = serializer.instance

        old_values = {}

        for field, new_value in serializer.validated_data.items():
            old_value = getattr(room, field)

            if old_value != new_value:
                old_values[field] = old_value

        room = serializer.save()

        changes = {}

        for field in old_values:
            changes[field] = {
                'old': old_values[field],
                'new': getattr(room, field)
            }

        RoomService.broacast_room_event(
            room=RoomReadSerializer(room).data,
            event_type='room_updated'
        )

        RoomService.log_room_update(
            room=room,
            request=request,
            changes=changes
        )

        return room

    @staticmethod
    def broacast_room_event(room, event_type):
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'rooms_all',
            {
                'type': event_type,
                'room': room
            }
        )
        
