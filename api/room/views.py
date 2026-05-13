from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.room.models import Room
from api.room.serializers import RoomSerializer
from api.room.services import RoomService

class RoomListCreateView(ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

class RoomDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

class RoomStatusListView(ListAPIView):
    serializer_class = RoomSerializer

    def get_queryset(self):
        status = self.request.query_params.get("status")
        return RoomService.get_all_by_status(status)