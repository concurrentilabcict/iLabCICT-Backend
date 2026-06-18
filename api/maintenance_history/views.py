
from rest_framework.generics import ListAPIView 
from api.maintenance_history.models import MaintenanceHistory
from api.maintenance_history.serializers import MaintenanceHistorySerializer
from api.maintenance_history.services import MaintenanceHistoryServices


class MaintenanceHistoryListView(ListAPIView):
    queryset = MaintenanceHistory.objects.all()
    serializer_class = MaintenanceHistorySerializer


class MaintenanceHistoryByComputerCode(ListAPIView):
    serializer_class = MaintenanceHistorySerializer
    
    def get_queryset(self):
        computer_code = self.request.query_params.get("computer-code")
        return MaintenanceHistoryServices.get_all_maintenance_history_by_computer(computer_code)