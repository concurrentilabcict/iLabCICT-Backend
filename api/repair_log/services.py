from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.notification.services import NotificationService

class RepairLogService:
    
    @staticmethod
    def get_all(
        technician_id=None,
        date=None):
        
        queryset = RepairLog.objects.all()

        if technician_id is not None:
            queryset = queryset.filter(technician_id=technician_id)
        
        if date is not None:
            queryset = queryset.filter(created_at__date=date)

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

        NotificationService.create_new_ticket_notification(
            receiver_id=ticket.reported_by,
            title='Ticket has been resolved!',
            ticket_id=ticket.id
            )
        
        ticket.save()
