
from api.maintenance_history.models import MaintenanceHistory
class MaintenanceHistoryServices:

    @staticmethod
    def get_all_maintenance_history_by_computer(computer_code=None):
        queryset = MaintenanceHistory.objects.filter(computer=computer_code)
        return queryset
