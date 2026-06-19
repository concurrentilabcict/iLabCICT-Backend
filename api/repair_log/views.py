from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogReadSerializer, RepairLogWriteSerializer
from api.repair_log.services import RepairLogService

class RepairLogListCreateView(ListCreateAPIView):
    queryset = RepairLog.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RepairLogWriteSerializer
        
        return RepairLogReadSerializer
    
class RepairLogDetailView(RetrieveAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogReadSerializer
    
class RepairLogByTechnicianListView(ListAPIView):
    serializer_class = RepairLogReadSerializer

    def get_queryset(self):
        technician_id = self.request.query_params.get("technician-id")
        return RepairLogService.get_all_by_technician(technician_id)