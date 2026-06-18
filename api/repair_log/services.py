from api.repair_log.models import RepairLog
from api.ticket.models import Ticket
from api.maintenance_history.models import MaintenanceHistory
from api.notification.services import NotificationService
from api.computer.models import Computer
from api.user.models import User

class RepairLogService:

    @staticmethod
    def get_all_by_technician(technician_id=None):
        queryset = RepairLog.objects.all()

        if technician_id:
            queryset = queryset.filter(technician=technician_id)

        return queryset
    
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
        
        ticket.status = 'resolved'
        ticket.save()

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.reported_by,
            title='Ticket has been resolved!',
            content={
                'header':ticket.title,
                'body': ticket.complaint_description,
                'ticket-status': ticket.status 
            }   
            )


