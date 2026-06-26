from api.room.models import Room
from rest_framework.exceptions import ValidationError

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

        queryset = Room.objects.all()

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
            raise ValidationError({
                'message': f'Invalid room status'
            })
        
        if building and building not in allowed_building_names:
            raise ValidationError({
                'message': f'Invalid building name'
            })
        
        if isinstance(room, bool):
            raise ValidationError({
                'message': f'Invalid room name'
            })
        

        

        
