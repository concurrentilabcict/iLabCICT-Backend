from api.room.models import Room

class RoomService:

    @staticmethod
    def get_all(status=None,
                building=None,
                room=None):
        
        queryset = Room.objects.all()

        if status is not None:
            queryset = queryset.filter(status=status)
        
        if building is not None: 
            queryset = queryset.filter(building_name=building)
        
        if room is not None:
            queryset = queryset.filter(room_name=room)

        return queryset