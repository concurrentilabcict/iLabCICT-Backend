from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView, RetrieveAPIView
from api.room.models import Room
from api.room.serializers import RoomReadSerializer, RoomWriteSerializer, RoomAndComputerListSerializer
from api.room.services import RoomService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician, IsStaff
from api.computer.models import Computer
from api.computer.serializers import ComputerReadSerializer
from django.db.models import Count, Q
from api.ticket.models import Ticket
import time
from rest_framework.response import Response
from django.db import connection

class RoomListCreateView(ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return RoomWriteSerializer
        return RoomReadSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        
        return [IsAuthenticated(), IsStaff()]

    def get_queryset(self):
        return RoomService.get_all(
            status=self.request.query_params.get('status'),
            building=self.request.query_params.get('building-name'),
            room=self.request.query_params.get('room-name'),
            include=self.request.query_params.get("include", ""),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include"] = self.request.query_params.get("include", "")
        return context
    
class RoomDetailView(RetrieveUpdateDestroyAPIView):
    queryset = (Room.objects
                    .select_related('assigned_custodian')
                    .prefetch_related('computers')
                    .annotate(computer_count=Count('computers', distinct=True),
                              computer_count_with_active_issues=Count(
                                'computers',
                                filter=Q(computers__tickets__status=Ticket.TicketStatus.ONGOING),
                                distinct=True
                              ))
                    )
    
    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return RoomWriteSerializer
        return RoomReadSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]
        elif self.request.method in ('PATCH', 'PUT'):       
            return [IsAuthenticated(), IsAdmin()]
        
        return [IsAuthenticated(), IsStaff()]
    
class RoomAllComputersDetailView(RetrieveAPIView):
    serializer_class = RoomAndComputerListSerializer

    permission_classes = [IsAuthenticated, IsStaff]

    def get_queryset(self):
        room_id = self.kwargs['pk']

        return (
            Room.objects
            .select_related('assigned_custodian')
            .prefetch_related('computers')
            .annotate(total_computer=Count('computers'))
            .filter(id=room_id)
        )
    
class RoomWithComputerCodeDetailView(RetrieveAPIView):
    serializer_class = ComputerReadSerializer

    permission_classes = [IsAuthenticated, IsStaff]

    def get_queryset(self):
        computer_code = self.kwargs['uk']
        room_id = self.kwargs['pk']

        return Computer.objects.select_related('room').filter(
            room_id=room_id,
            computer_code=computer_code)
    
class RoomNameWithComputerCodeDetailView(RetrieveAPIView):
    serializer_class = ComputerReadSerializer

    permission_classes = [IsAuthenticated, IsStaff]

    lookup_field = 'computer_code'
    lookup_url_kwarg ='uk'

    def get_queryset(self):
        computer_code = self.kwargs['uk']
        room_name = self.kwargs['room']

        return Computer.objects.select_related('room').filter(
            room__room_name=room_name,
            computer_code=computer_code)
    
class RoomNameAllComputersDetailView(RetrieveAPIView):
    serializer_class = RoomAndComputerListSerializer
    permission_classes = [IsAuthenticated, IsStaff]

    lookup_field = "room_name"
    lookup_url_kwarg = "room"

    def get_queryset(self):
        return (
            Room.objects
            .select_related("assigned_custodian")
            .prefetch_related("computers")
            .annotate(total_computer=Count("computers"))
        )
