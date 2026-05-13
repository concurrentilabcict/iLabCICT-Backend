from api.room.models import Room

class RoomService:

    @staticmethod
    def get_all_by_status(status=None):
        queryset = Room.objects.all()

        if status:
            queryset = queryset.filter(status=status)

        return queryset