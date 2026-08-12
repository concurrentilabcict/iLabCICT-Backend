from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.notification.services import NotificationService
from rest_framework.exceptions import ValidationError
from api.ticket.models import Ticket
from api.common.utils.date_checker import is_invalid_date_format
from api.user.models import User
from api.notification.models import Notification
from api.ticket.services import TicketService
from api.ticket.serializers import TicketReadSerializer
from api.audit_logs.services import AuditLogsService
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync  
from api.cursor import CursorService
from django.db.models import Q
class RepairLogService:

    PAGE_SIZE = 15

    @staticmethod
    def get_paginated_repair_logs(user, cursor= None, query_search=None):
        queryset = RepairLogService.get_all(user=user)

        if query_search:
            queryset = RepairLogService.search_repair_logs(
                queryset=queryset,
                query_search=query_search
            )

        if cursor:
            cursor_data = CursorService.decode_cursor(cursor=cursor)

            if cursor_data is None: 
                raise ValueError('Invalid cursor')

            created_at = cursor_data['created_at']
            repair_log_id = cursor_data['id']

            queryset = queryset.filter(
                Q(created_at__lt=created_at) |
                Q(
                    created_at=created_at,
                    id__lt=repair_log_id
                )
            )

        queryset = queryset.order_by(
            '-created_at',
            '-id'
        )

        repair_logs = list(
            queryset[:RepairLogService.PAGE_SIZE + 1]
        )

        has_more = len(repair_logs) > RepairLogService.PAGE_SIZE

        repair_logs = repair_logs[:RepairLogService.PAGE_SIZE]

        next_cursor = None

        if has_more and repair_logs:
            next_cursor = CursorService.encode_cursor(
                repair_logs[-1]
            )

        return repair_logs, next_cursor
    
    @staticmethod
    def get_all(
        user,
        technician_id=None,
        date=None):

        RepairLogService.validate_filters(
            technician_id=technician_id,
            date=date
            )

        queryset = RepairLog.objects.select_related('ticket',
                                                    'ticket__reported_by',
                                                    'ticket__assigned_to',
                                                    'ticket__room',
                                                    'ticket__computer',)

        if user.role == User.UserRole.TECHNICIAN:
            queryset = queryset.filter(technician_id=user.id)
        
        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        return queryset.order_by('-created_at', '-id')
    
    @staticmethod
    def validate_filters(technician_id,date):
        
        if technician_id is not None:
            try:
                technician_id = int(technician_id)
            except (TypeError, ValueError):
                raise ValidationError('Invalid technician-id.')
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')
    
    @staticmethod 
    def record_maintenance_history(ticket, notes, type, technician, computer, repair_log, request):
        RepairLogService.update_ticket_to_resolved(ticket)

        maintenance_history = MaintenanceHistory.objects.create(
            computer_id=computer.id,
            technician_id=technician.id,
            maintenance_notes=notes,
            maintenance_type=type,
            date_performed=ticket.updated_at,
            repair_log=repair_log
        )

        AuditLogsService.log(
            request=request,
            performed_by=technician,
            action_title='Report ticket resolved',
            action_summary=f'{technician.get_full_name()} has resolved a report ticket.',
            metadata={
                'repair_log_id': repair_log.id,
                'maintenance_history_id': maintenance_history.id,
                'ticket_id': ticket.id,
                'room_id': ticket.room_id,
                'reported_by_id': ticket.reported_by_id,
                'assigned_to_id': ticket.assigned_to_id,
                'status': ticket.status,
            }
        )

    
    def update_ticket_to_resolved(ticket):
        
        ticket.status = Ticket.TicketStatus.RESOLVED

        NotificationService.create_new_ticket_notification(
            recipient_id=ticket.reported_by_id,
            title='Report Ticket Resolved!',
            entity=ticket,
            event=Notification.NotificationEventTypes.UNICAST_FACULTY,
            role=User.UserRole.FACULTY
        )

        ticket.save()

        groups = {
            f'tickets_user_{ticket.reported_by_id}',
            f'tickets_user_{ticket.assigned_to_id}',
            'tickets_admins', 
        }

        TicketService.send_ticket_event(
            groups=list(groups),
            event_type='ticket_updated',
            ticket=TicketReadSerializer(ticket).data
        )

    @staticmethod
    def broadcast_repair_log_event(groups, repair_log):
        channel_layer = get_channel_layer()

        for group in set(groups):
            async_to_sync(channel_layer.group_send)(
                group,
                {
                    'type': 'repair_log_created',
                    'repair_log': repair_log
                }
            )

    @staticmethod
    def search_repair_logs(query_search, queryset):
        terms = query_search.strip().split()

        for term in terms:
            queryset = queryset.filter(
                Q(repair_log_code__icontains=term) |
                Q(title__icontains=term) |
                Q(repair_notes__icontains=term) |
                Q(technician__first_name__icontains=term) |
                Q(technician__last_name__icontains=term)
            )

        return queryset


