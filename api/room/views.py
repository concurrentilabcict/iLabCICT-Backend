from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.room.models import Room
from api.room.serializers import RoomSerializer

class RoomListCreateView(ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

class RoomDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer