from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogSerializer
from api.repair_log.services import RepairLogService

class RepairLogListCreateView(ListCreateAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer

    def perform_create(self, serializer):
        repair_log = serializer.save()
        RepairLogService.record_maintenance_history(repair_log.ticket_id, repair_log.notes)

class RepairLogDetailView(RetrieveUpdateDestroyAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer


class RepairLogByTechnicianListView(ListAPIView):
    serializer_class = RepairLogSerializer

    def get_queryset(self):
        technician_id = self.request.query_params.get("technician-id")
        return RepairLogService.get_all_by_technician(technician_id)