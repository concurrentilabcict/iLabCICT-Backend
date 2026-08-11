from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from api.report.models import Report
from api.report.serializers import ReportSerializer
from api.report.services import ReportService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from django.db.models import Q

class ReportListCreateView(ListCreateAPIView):
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

    PAGE_SIZE = 15
    
    def create(self, request, *args, **kwargs):
        return ReportService.generate_report_content(request)
    
    def get_queryset(self):
        queryset = ReportService.get_all(
            technician_id=self.request.user.id,
            status=self.request.query_params.get('status'),
            date=self.request.query_params.get('date'),
        )

        before_id = self.request.query_params.get('before-id')
        before_created_at = self.request.query_params.get('before-id')

        if  before_created_at and before_id:

            before_created_at = parse_datetime(before_created_at)

            queryset = queryset.filter(
                Q(created_at__lt=before_created_at) |
                Q(
                    created_at=before_created_at,
                    id__lt=before_id
                )
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        count = queryset.count() 

        reports = list(queryset[:self.PAGE_SIZE + 1])

        has_more = len(reports) > self.PAGE_SIZE
        reports = reports[:self.PAGE_SIZE]

        serializer = self.get_serializer(reports, many=True)

        next_url = None
        if has_more and reports:
            last = reports[-1]

            next_url = (
                f'{request.build_absolute_uri(request.path)}'
                f'?before-id={last.id}'
                f'&before-created-at={last.created_at.isoformat().replace("+00:00", "Z")}'
            )

        return Response({
            'count': count,
            'next': next_url,
            'previous': None,
            'results': serializer.data,
        })




    
class ReportDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

