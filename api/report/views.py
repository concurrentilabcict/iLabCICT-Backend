from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from api.report.models import Report
from api.report.serializers import ReportSerializer
from api.report.services import ReportService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician
from rest_framework.response import Response

class ReportListCreateView(ListCreateAPIView):
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

    def create(self, request, *args, **kwargs):
        return ReportService.generate_report_content(request)

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')
        query_search = request.query_params.get('q')
        date = request.query_params.get('date')
        technician_id = request.query_params.get('technician_id')
        status = request.query_params.get('status')

        try:
            reports = (
                ReportService.get_reports(
                    user=request.user,
                    cursor=cursor,
                    query_search=query_search,
                    date=date,
                    technician_id=technician_id,
                    status=status
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )


        return Response({
            'results': ReportSerializer(
                reports, many=True
            ).data,
        })


class ReportDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

