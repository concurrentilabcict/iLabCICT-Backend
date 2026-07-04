from api.room.models import Room
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Q
from api.ticket.models import Ticket
class RoomService:

    @staticmethod
    def get_all(status=None,
                building=None,
                room=None):
        
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
        

        
