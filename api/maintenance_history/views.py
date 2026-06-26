
from rest_framework.generics import ListAPIView,RetrieveAPIView
from api.maintenance_history.models import MaintenanceHistory
from api.maintenance_history.serializers import MaintenanceHistorySerializer
from api.maintenance_history.services import MaintenanceHistoryServices

class MaintenanceHistoryListView(ListAPIView):
    serializer_class = MaintenanceHistorySerializer

    def get_queryset(self):
        return MaintenanceHistoryServices.get_all(
            type=self.request.query_params.get('type'),
            computer_id=self.request.query_params.get('computer-id'),
            technician_id=self.request.query_params.get('technician-id'),
            date=self.request.query_params.get('date')
        )

class MaintenanceHistoryDetailView(RetrieveAPIView):
    queryset = MaintenanceHistory.objects.all()
    serializer_class = MaintenanceHistorySerializer
