from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.room.models import Room
from api.room.serializers import RoomSerializer
from api.room.services import RoomService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician, IsFaculty, IsStaff

class RoomListCreateView(ListCreateAPIView):
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        
        return [IsAuthenticated, IsStaff()]

    def get_queryset(self):
        return RoomService.get_all(
            status=self.request.query_params.get('status'),
            building=self.request.query_params.get('building-name'),
            room=self.request.query_params.get('room-name')
        )
    

class RoomDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]
        elif self.request.method in ('PATCH', 'PUT'):       
            return [IsAuthenticated(), IsAdmin() | IsTechnician()]
        
        return [IsAuthenticated(), IsStaff()]