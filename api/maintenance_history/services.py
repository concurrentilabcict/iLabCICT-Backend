
from api.maintenance_history.models import MaintenanceHistory
class MaintenanceHistoryServices:
    
    @staticmethod
    def get_all(type=None,
                computer_id=None,
                technician_id=None,
                date=None):
        
        queryset = MaintenanceHistory.objects.all()

        if type is not None:
            queryset = queryset.filter(maintenance_type=type)
        
        if computer_id is not None:
            queryset = queryset.filter(computer_id=computer_id)

        if technician_id is not None:
            queryset = queryset.filter(technician_id=technician_id)

        if date is not None:
            queryset = queryset.filter(date_performed__date=date)

        return queryset
