from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.room.models import Room
from api.room.serializers import RoomSerializer
from api.room.services import RoomService

class RoomListCreateView(ListCreateAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        return RoomService.get_all(
            status=self.request.query_params.get('status'),
            building=self.request.query_params.get('building_name'),
            room=self.request.query_params.get('room_name')
        )
    
    
class RoomDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

