from api.room.models import Room
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Q
from api.ticket.models import Ticket
from api.audit_logs.services import AuditLogsService 
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.room.serializers import RoomReadSerializer
class RoomService:

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
                        updated_fields,
                        old_name,
                        old_technician_id,
                        old_custodian_id):
        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='Room updated',
            action_summary=f"{request.user.get_full_name()} updated room '{room.room_name}'.",
            metadata={
                'room_id': room.id,
                'updated_fields': updated_fields,
                'old_room_name': old_name,
                'new_room_name': room.room_name,
                'old_assigned_technician_id': old_technician_id,
                'new_assigned_technician_id': room.assigned_technician_id,
                'old_assigned_custodian_id': old_custodian_id,
                'new_assigned_custodian_id': room.assigned_custodian_id
            }
        )

    @staticmethod
    def update_room(serializer, request):
        room = serializer.instance

        old_name = room.room_name
        old_technician_id = room.assigned_technician_id
        old_custodian_id = room.assigned_custodian_id

        room = serializer.save()

        RoomService.broacast_room_event(
            room=RoomReadSerializer(room).data,
            event_type='room_updated'
        )

        RoomService.log_room_update(
            room=room,
            request=request,
            updated_fields=list(serializer.validated_data.keys()),
            old_name=old_name,
            old_technician_id=old_technician_id,
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
        
