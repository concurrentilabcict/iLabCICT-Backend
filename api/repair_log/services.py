from api.repair_log.models import RepairLog
from api.ticket.models import Ticket
from api.maintenance_history.models import MaintenanceHistory
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
    def record_maintenance_history(ticket_id, notes):
        ticket = Ticket.objects.get(id=ticket_id)
        computer = Computer.objects.get(id=ticket.computer_id)

        technician = User.objects.get(id=ticket_id.assigned_to_id)
        full_name = technician.first_name + " " + technician.last_name 
        ticket.status = 'resolved'
        ticket.save()

        MaintenanceHistory.objects.create(
            computer=computer,
            computer_id=computer.id,
            technician_id=ticket.assigned_to_id,
            performed_by=full_name,
            maintenance_notes=notes,
            maintenance_type=None,
            date_performed=ticket.updated_at,
        )
        

