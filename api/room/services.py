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
from api.common.utils.date_checker import is_invalid_date_format
class RoomService:

    PAGE_SIZE=15

    @staticmethod
    def get_rooms(cursor=None, include="", query_search=None, status=None, room_name=None, building_name=None, date=None):
        queryset = RoomService.get_all(
            query_search=query_search,
            status=status,
            room=room_name,
            building=building_name,
            include=include
        )

        if query_search:
            queryset = RoomService.search_rooms(
                query_search=query_search,
                qeuryset=queryset
            )
        return queryset

    @staticmethod
    def get_computers_room_id(room_id=None, cursor=None, query_search=None, status=None, date=None):

        computers_queryset = (
                    Computer.objects
                    .filter(room_id=room_id)
                    .order_by('id')
                )

        if status and query_search:
            raise ValidationError('Search and filters cannot be combined.')

        if status:
            if status not in Computer.ComputerStatus.values:
                raise ValidationError('Invalid status')

            computers_queryset = computers_queryset.filter(computer_status=status)

        if date:
            if is_invalid_date_format(date):
                raise ValidationError('Date format must be in YYYY-MM-DD')

            computers_queryset = computers_queryset.filter(created_at__date=date)
        
        if query_search:
            computers_queryset = RoomService.search_computers(
                querys_search=query_search,
                queryset=computers_queryset
            )

        queryset = (Room.objects
                    .select_related('assigned_custodian')
                    .prefetch_related(
                        Prefetch(
                            'computers',
                            queryset=computers_queryset,
                            to_attr='initial_computers'
                        ) 
                    )
                    .annotate(total_computers=Count('computers'))
                    .filter(id=room_id))

        room = queryset.first()

        if room is None:
            return None

        return room


    @staticmethod
    def get_all(status=None,
                building=None,
                room=None,
                include="",
                query_search=None,
                date=None):
        
        RoomService.validate_filters(
            status=status,
            building=building,
            room=room,
            query_search=query_search,
            date=date
            )

        queryset = (Room.objects
                    .select_related('assigned_custodian','assigned_technician')
                    .annotate(computer_count=Count('computers', distinct=True),
                                computer_count_with_active_issues=Count(
                                'computers',
                                filter=Q(computers__tickets__status__in=[
                                        Ticket.TicketStatus.OPEN,
                                        Ticket.TicketStatus.ONGOING,
                                    ]),
                                distinct=True
                                ))
                    .order_by('id')
                    )
        
        if "computers" in include.split(","):
            queryset = queryset.prefetch_related("computers")

        if status is not None:
            queryset = queryset.filter(status=status)
        
        if building is not None: 
            queryset = queryset.filter(building_name=building)
        
        if room is not None:
            queryset = queryset.filter(room_name=room)

        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        return queryset
    
    @staticmethod
    def validate_filters(status,building,room, query_search=None, date=None):
        allowed_room_statuses = Room.RoomStatus.values
        allowed_building_names = Room.BuildingName.values

        if query_search and (status or building or room):
            raise ValidationError('Search and filters cannot be combined.')

        if status and status not in allowed_room_statuses:
            raise ValidationError('Invalid room status')
        
        if building and building not in allowed_building_names:
            raise ValidationError('Invalid building name')
        
        if isinstance(room, bool):
            raise ValidationError('Invalid room name')

        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')

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

    @staticmethod
    def search_rooms(query_search, qeuryset):
        terms = query_search.strip().split()

        for term in terms:
            qeuryset = qeuryset.filter(
                Q(room_name__icontains=term) |
                Q(building_name__icontains=term) |
                Q(assigned_custodian__first_name__icontains=term) |
                Q(assigned_custodian__last_name__icontains=term) |
                Q(assigned_technician__first_name__icontains=term) |
                Q(assigned_technician__last_name__icontains=term) |
                Q(floor_number__icontains=term) |
                Q(status__icontains=term)
            )

        return qeuryset

    @staticmethod
    def search_computers(querys_search, queryset):
        terms = querys_search.strip().split()

        for term in terms:
            queryset = queryset.filter(
                Q(computer_code__icontains=term) |
                Q(computer_status__icontains=term)
            )

        return queryset

        
