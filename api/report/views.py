from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView

from api.report.models import Report
from api.report.serializers import ReportSerializer
from api.report.services import ReportService
from rest_framework.response import Response
from api.repair_log.serializers import RepairLogSerializer


class ReportListCreateView(ListCreateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def create(self, request, *args, **kwargs):
        return ReportService.generate_report_content(request)
    
class ReportDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

class ReportByTechnicianListView(ListAPIView):
    serializer_class = ReportSerializer

    def get_queryset(self):
        technician_id = self.request.query_params.get("technician-id")
        return ReportService.get_all_by_technician(technician_id)
