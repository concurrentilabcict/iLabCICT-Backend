from api.ticket.models import Ticket
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.notification.services import NotificationService
from django.db import transaction
from api.common.utils.date_checker import is_invalid_date_format
from rest_framework.exceptions import ValidationError
from api.user.models import User
from django.db.models import Q
from api.ticket.serializers import TicketReadSerializer
class TicketService:

    @staticmethod
    def get_all(user,
                status=None, 
                technician_id=None, 
                date=None, 
                type=None):
        
        TicketService.validate_filters(
            status=status,
            technician_id=technician_id,
            date=date,
            type=type
        )

        queryset = Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
            )
        
        if user.role == User.UserRole.TECHNICIAN:
            queryset = queryset.filter(
                Q(assigned_to=user) | Q(assigned_to__isnull=True)
                )

        elif user.role == User.UserRole.FACULTY:
            queryset = queryset.filter(reported_by_id=user.id)

        elif user.role == User.UserRole.ADMIN and technician_id:
            queryset = queryset.filter(assigned_to_id=technician_id)

        if status is not None:
            queryset = queryset.filter(status=status)
        
        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        if type is not None:
            queryset = queryset.filter(type=type)
        
        return queryset
    
    @staticmethod
    def validate_filters(status,technician_id,date,type):
        allowed_ticket_statuses = Ticket.TicketStatus.values
        allowed_ticket_types = Ticket.TicketType.values

        if status and status not in allowed_ticket_statuses:
            raise ValidationError('Invalid ticket status')
        
        if type and type not in allowed_ticket_types:
            raise ValidationError('Invalid ticket type')
        
        if technician_id is not None:
            try:
                technician_id = int(technician_id)
            except (TypeError, ValueError):
                raise ValidationError('Invalid technician-id')
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')

    
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

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'ticket_created',
                'ticket': TicketReadSerializer(ticket).data
            }
        )

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.assigned_to,
            title='New Ticket Created!',
            ticket_id=ticket.id
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

    
    @staticmethod
    @transaction.atomic()
    def claim_ticket(instance, technician, status):
        updated = (
                    Ticket.objects
                    .filter(
                        id=instance.id,
                        assigned_to__isnull=True
                    )
                    .update(
                        assigned_to=technician,
                        status=status
                    )
                )

        if updated:
            return Ticket.objects.select_related("reported_by",
                                "assigned_to",
                                "room",
                                "computer"
                            ).get(id=instance.id)

        instance.refresh_from_db()
        
        if instance.assigned_to != technician:
            raise ValidationError("Ticket has already been claimed.")

        instance.status = status
        instance.save(update_fields=["status"])

        return instance

    @staticmethod
    def update_ticket_to_ongoing(instance):
        instance.status = Ticket.TicketStatus.ONGOING
        instance.save(update_fields=["status"])
        return instance


    
