from api.ticket.models import Ticket
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.notification.services import NotificationService
from django.db import transaction
from api.common.utils.date_checker import is_invalid_date_format
from rest_framework.exceptions import ValidationError
from api.user.models import User
from django.db.models import Q
from api.notification.models import Notification
from api.request_history.models import RequestHistory
from api.ticket.serializers import TicketReadSerializer
from api.audit_logs.services import AuditLogsService

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
                    Q(assigned_to=user)
                    | Q(status=Ticket.TicketStatus.OPEN)
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
    def create_ticket(reported_by, validated_data, request):

        room = validated_data.get('room')
        validated_data.pop('status', None)
        ticket_type = validated_data.get('type')

        assigned_technician = room.assigned_technician

        ticket = Ticket.objects.create(
            status=Ticket.TicketStatus.OPEN,
            reported_by=reported_by,
            assigned_to=assigned_technician,
            **validated_data
        )

        NotificationService.create_new_ticket_notification(
            recipient_id=None,
            title='New Ticket Created!',
            entity=ticket,
            role= User.UserRole.TECHNICIAN,
            event=Notification.NotificationEventTypes.MULTICAST_TECHNICIAN
        )

        AuditLogsService.log(
            request=request,
            performed_by=reported_by,
            action_title='Ticket created',
            action_summary=f'{reported_by.get_full_name()} created a {ticket_type.lower()} ticket.',
            metadata={
                'ticket_id': ticket.id,
                'ticket_title': ticket.title,
                'ticket_type': ticket.type,
                'room_id': ticket.room_id,
                'assigned_to_id': ticket.assigned_to_id,
                'status': ticket.status,
            }
        )

        groups = {
            f'tickets_user_{ticket.reported_by_id}',
            'tickets_technicians',
            'tickets_admins',
        }

        TicketService.send_ticket_event(
            groups=list(groups),
            event_type='ticket_created',
            ticket=TicketReadSerializer(ticket).data
        )

        return ticket
    
    @staticmethod
    def update_ticket(instance, validated_data, technician, request):

        status = validated_data.get("status", instance.status)
        #for ticket claiming
        reassigned = (
            Ticket.objects
            .filter(
                id=instance.id,
                status=Ticket.TicketStatus.OPEN
            )
            .update(
                assigned_to=technician,
                status=Ticket.TicketStatus.ONGOING
            )
        )

        if not reassigned:
            instance.refresh_from_db()
            instance.status = status
            instance.save(update_fields=["status"])

        ticket = Ticket.objects.select_related(
                    "reported_by",
                    "assigned_to",
                    "room",
                    "computer",
                ).get(pk=instance.pk)

        if reassigned:
            
            TicketService.handle_ticket_reassigned(
                ticket=ticket,
                technician=technician,
                request=request,
                instance=instance
            )

        if ticket.status == Ticket.TicketStatus.RESOLVED and ticket.type == Ticket.TicketType.REQUEST:

            TicketService.handle_resolved_request_tickets(
                ticket=ticket,
                technician=technician,
                request=request
            )

        elif ticket.status != instance.status:

            TicketService.handle_ticket_status_change(
                ticket=ticket,
                technician=technician,
                request=request,
                instance=instance
            )

        TicketService.handle_ticket_broadcast(
            reassigned=reassigned,
            ticket=ticket
        )

        return ticket


    @staticmethod
    def handle_ticket_reassigned(ticket, technician, request, instance):
        NotificationService.create_new_ticket_notification(
                        recipient_id=ticket.reported_by_id,
                        title='Ticket reassigned!',
                        entity=ticket,
                        event=Notification.NotificationEventTypes.UNICAST_FACULTY,
                        role= User.UserRole.FACULTY
                            )
        NotificationService.update_ticket_technician_recipient(
            entity_id=ticket.id,
        )
        NotificationService.create_new_ticket_notification(
            recipient_id=ticket.assigned_to_id,
            title='Ticket assigned to You',
            entity=ticket,
            event=Notification.NotificationEventTypes.UNICAST_TECHNICIAN,
            role = User.UserRole.TECHNICIAN
        )
        AuditLogsService.log(
            request=request,
            performed_by=technician,
            action_title='Ticket reassigned',
            action_summary=f'{technician.get_full_name()} claimed a ticket.',
            metadata={
                'ticket_id': ticket.id,
                'status': ticket.status,
                'old_assigned_to_id': instance.assigned_to_id,
                'new_assigned_to_id': ticket.assigned_to_id
            }
        )

    @staticmethod
    def handle_resolved_request_tickets(ticket, technician, request):

        NotificationService.create_new_ticket_notification(
                            recipient_id=ticket.reported_by_id,
                            title='Request ticket resolved!',
                            entity=ticket,
                            event=Notification.NotificationEventTypes.UNICAST_FACULTY,
                            role= User.UserRole.FACULTY
                                )
        request_history = RequestHistory.objects.create(
            room=ticket.room,
            technician=ticket.assigned_to,
            ticket=ticket
        )

        AuditLogsService.log(
            request=request,
            performed_by=technician,
            action_title='Request ticket resolved',
            action_summary=f'{technician.get_full_name()} has resolved a request ticket.',
            metadata={
                'request_history_id': request_history.id,
                'ticket_id': ticket.id,
                'ticket_type': ticket.type,
                'room_id': ticket.room_id,
                'reported_by_id': ticket.reported_by_id,
                'assigned_to_id': ticket.assigned_to_id,
                'status': ticket.status,
            }
        )

    @staticmethod
    def handle_ticket_status_change(ticket, technician, instance, request):

        NotificationService.create_new_ticket_notification(
            recipient_id=ticket.reported_by_id,
            title='Ticket status updated!',
            entity=ticket,
            event=Notification.NotificationEventTypes.UNICAST_FACULTY,
            role= User.UserRole.FACULTY
                )

        AuditLogsService.log(
            request=request,
            performed_by=technician,
            action_title=f'{ticket.type} ticket updated',
            action_summary=f'{technician.get_full_name()} updated a ${ticket.type} ticket status to ${ticket.status}.',
            metadata={
                'ticket_id': ticket.id,
                'new_status': ticket.status,
                'previous_status': instance.status
            }
        )

    @staticmethod
    def handle_ticket_broadcast(reassigned, ticket):
        groups = {
            'tickets_admins',
            f'tickets_user_{ticket.reported_by_id}'
        }

        if ticket.assigned_to_id and ticket.status == Ticket.TicketStatus.RESOLVED and ticket.type == Ticket.TicketType.REQUEST:
            groups.add(f'tickets_user_{ticket.assigned_to_id}')

        if reassigned:
            TicketService.send_ticket_event(
                groups=['tickets_technicians'],
                event_type="ticket_reassigned",
                ticket=TicketReadSerializer(ticket).data,
            )

        TicketService.send_ticket_event(
            groups=list(groups),
            event_type="ticket_updated",
            ticket=TicketReadSerializer(ticket).data,
        )

    

    @staticmethod
    def send_ticket_event(groups, event_type, ticket):
        channel_layer = get_channel_layer()

        for group in set(groups):
            async_to_sync(channel_layer.group_send)(
                group,
                {
                    'type': event_type,
                    'ticket': ticket
                }
            )
    
    
