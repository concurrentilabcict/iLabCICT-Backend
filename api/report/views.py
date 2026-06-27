from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from api.report.models import Report
from api.report.serializers import ReportSerializer
from api.report.services import ReportService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician

class ReportListCreateView(ListCreateAPIView):
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]
    
    def create(self, request, *args, **kwargs):
        return ReportService.generate_report_content(request)
    
    def get_queryset(self):
        return ReportService.get_all(
            technician_id=self.request.query_params.get('technician-id'),
            status=self.request.query_params.get('status'),
            date=self.request.query_params.get('date'),
        )
    
class ReportDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

