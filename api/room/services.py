from api.room.models import Room
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Q, Prefetch
from api.computer.models import Computer
from api.ticket.models import Ticket
from api.audit_logs.services import AuditLogsService 
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.room.serializers import RoomReadSerializer
class RoomService:

    @staticmethod
    def get_computers_room_id(room_id=None):

        queryset = (Room.objects
                    .select_related('assigned_custodian')
                    .prefetch_related(
                        Prefetch(
                            'computers',
                            queryset=Computer.objects.order_by('id')[:15],
                            to_attr='initial_computers'
                        ) 
                    )
                    .annotate(total_computer=Count('computers'))
                    .filter(id=room_id)
                    .first()
                    )
        
        if room_id is None:
            return queryset.none()

        return queryset

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
        
