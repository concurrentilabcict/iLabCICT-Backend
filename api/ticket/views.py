from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.ticket.models import Ticket
from api.ticket.serializers import TicketReadSerializer, TicketWriteSerializer
from api.ticket.services import TicketService
from api.permissions import IsAdmin, IsTechnician, IsFaculty, IsTicketAccess
from rest_framework.permissions import IsAuthenticated

class TicketListCreateView(ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsFaculty()]
            
        return [IsAuthenticated(), IsTicketAccess()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketWriteSerializer
        
        return TicketReadSerializer
    
    def get_queryset(self):
        return TicketService.get_all(
            user=self.request.user,
            status=self.request.query_params.get('status'),
            technician_id=self.request.query_params.get('technician-id'),
            type=self.request.query_params.get('type'),
            date=self.request.query_params.get('date')
        )
    
    def perform_create(self, serializer):
        TicketService.create_ticket(serializer)

class TicketDetailView(RetrieveUpdateDestroyAPIView):

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsAdmin() | IsTechnician()]
        elif self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]

        return [IsAuthenticated(), IsTicketAccess()]
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return TicketWriteSerializer
        
        return TicketReadSerializer

    def get_queryset(self):
        return Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
        )
    
    def perform_update(self, serializer):
        TicketService.update_ticket(serializer)

    def perform_destroy(self, instance):
        TicketService.delete_ticket(instance)

    http_method_names = ['patch', 'delete', 'get']


