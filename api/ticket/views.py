from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.ticket.models import Ticket
from api.ticket.serializers import TicketReadSerializer, TicketWriteSerializer
from api.ticket.services import TicketService
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.notification.services import NotificationService

class TicketListCreateView(ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketWriteSerializer
        
        return TicketReadSerializer
    

    def get_queryset(self):
        return Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
        )
    
    def perform_create(self, serializer):
        ticket = serializer.save()
        
        ticket = Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
        ).get(pk=ticket.pk)

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.assigned_to,
            title='New Ticket Created!',
            content={
                'header': ticket.title,
                'body': ticket.complaint_description,
                'ticket-status': ticket.status
            }
        )

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_created',
                'ticket': TicketReadSerializer(ticket).data
            }
        )

class TicketDetailView(RetrieveUpdateDestroyAPIView):

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
        ticket = serializer.save()

        ticket = Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
        ).get(pk=ticket.pk)

        channel_layer = get_channel_layer()

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.reported_by,
            title='Ticket Status Updated!',
            content={
                'header': ticket.title,
                'body': ticket.complaint_description,
                'ticket-status': ticket.status
            }
        )

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_updated',
                'ticket': TicketReadSerializer(ticket).data
            }
        )

    def perform_destroy(self, instance):
        ticket_id = instance.id

        instance.delete()

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_deleted',
                'ticket_id': ticket_id
            }
        )

    http_method_names = ['patch', 'delete', 'get']

class TicketStatusListView(ListAPIView):
    serializer_class = TicketReadSerializer

    def get_queryset(self):
        status = self.request.query_params.get("status")
        return TicketService.get_all_by_status(status)