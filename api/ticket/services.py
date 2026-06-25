from api.ticket.models import Ticket
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.notification.services import NotificationService
from api.ticket.serializers import TicketReadSerializer
from django.db import transaction
class TicketService:

    @staticmethod
    def get_all(status=None, 
                technician=None, 
                date=None, 
                type=None):
        
        queryset = Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
            )
        
        if status is not None:
            queryset = queryset.filter(status=status)
        
        if technician is not None:
            queryset = queryset.filter(assigned_to_id=technician)
        
        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        if type is not None:
            queryset = queryset.filter(type=type)
        
        return queryset
    
    @staticmethod
    @transaction.atomic
    def create_ticket(serializer):
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
            ticket_id=ticket.id
        )

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_created',
                'ticket': TicketReadSerializer(ticket).data
            }
        )

        return ticket
    
    @staticmethod
    def update_ticket(serializer):
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
            ticket_id=ticket.id
        )

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_updated',
                'ticket': TicketReadSerializer(ticket).data
            }
        )

        return ticket
    
    @staticmethod
    def delete_ticket(instance):    
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
