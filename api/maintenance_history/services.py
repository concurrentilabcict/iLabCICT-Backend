
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
        
        queryset = MaintenanceHistory.objects.select_related('repair_log',
                                                             'repair_log__ticket')

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

        if computer_id is not None:
            try:
                computer_id = int(computer_id)
            except (TypeError, ValueError):
                raise ValidationError('Invalid computer-id.')
            
        if  technician_id is not None:
            try:
                technician_id = int(technician_id)
            except (TypeError, ValueError):
                raise ValidationError('Invalid technician-id.')

        if type and type not in allowed_maintenance_types:
            raise ValidationError('Invalid maintenance type')
        
        if is_invalid_date_format(date) and date is not None:
            raise ValidationError('Date format must be in YYYY-MM-DD')
        
        