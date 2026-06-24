from api.room.models import Room

class RoomService:

    @staticmethod
    def get_all_by_status(status=None):
        queryset = Room.objects.all()

        if status:
            queryset = queryset.filter(status=status)

        return queryset
    
    @staticmethod
    def get_all_by_building(building=None):
        queryset = Room.objects.all()

        if building:
            queryset = queryset.filter(building_name=building)
        
        return queryset
    
    @staticmethod
    def get_all_by_room_name(room=None):
        queryset = Room.objects.all()

        if room:
            queryset = queryset.filter(room_name=room)
        
        return queryset
        