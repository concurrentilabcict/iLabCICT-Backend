from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.notification.services import NotificationService
from rest_framework.exceptions import ValidationError
from api.ticket.models import Ticket
from api.common.utils.date_checker import is_invalid_date_format
from api.user.models import User

class RepairLogService:
    
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

        if technician_id and User.UserRole.ADMIN:
            queryset = queryset.filter(technician_id=technician_id)
        
        if date is not None:
            queryset = queryset.filter(created_at__date=date)

        return queryset
    
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
    def record_maintenance_history(ticket, notes, type, technician, computer):
        full_name = technician.first_name + " " + technician.last_name 
        RepairLogService.update_ticket_to_resolved(ticket)

        MaintenanceHistory.objects.create(
            computer=computer,
            computer_id=computer.id,
            technician_id=technician.id,
            performed_by=full_name,
            maintenance_notes=notes,
            maintenance_type=type,
            date_performed=ticket.updated_at,
        )

    
    def update_ticket_to_resolved(ticket):
        
        ticket.status = Ticket.TicketStatus.RESOLVED

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.reported_by,
            title='Ticket has been resolved!',
            ticket_id=ticket.id
            )
        
        ticket.save()
