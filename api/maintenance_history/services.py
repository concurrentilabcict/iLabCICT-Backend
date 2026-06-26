
from api.maintenance_history.models import MaintenanceHistory
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format
class MaintenanceHistoryServices:
    
    @staticmethod
    def get_all(type=None,
                computer_id=None,
                technician_id=None,
                date=None):
        
        MaintenanceHistoryServices.validate_filters(
            type=type,
            computer_id=computer_id,
            technician_id=technician_id,
            date=date        
            )
        
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

    @staticmethod
    def validate_filters(type,computer_id,technician_id,date):
        allowed_maintenance_types = MaintenanceHistory.MaintenanceTypes.values

        if type and type not in allowed_maintenance_types:
            raise ValidationError({
                'message': f'Invalid maintenance type'
            })
        
        if not isinstance(computer_id, int):
            raise ValidationError({
                'message': f'Invalid computer-id'
            })
        
        if not isinstance(technician_id, int):
            raise ValidationError({
                'message': f'Invalid technician-id'
            })
        
        if is_invalid_date_format(date):
            raise ValidationError({
                'message': f'Date format must be YYYY-MM-DD'
            })
        
        