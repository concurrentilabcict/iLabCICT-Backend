from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from api.report.models import Report
from api.report.serializers import ReportSerializer
from api.report.services import ReportService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician
from rest_framework.response import Response
from django.conf import settings
from urllib.parse import urlencode

class ReportListCreateView(ListCreateAPIView):
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

    def create(self, request, *args, **kwargs):
        return ReportService.generate_report_content(request)

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')
        query_search = request.query_params.get('q')

        try:
            reports, next_cursor = (
                ReportService.get_paginated_reports(
                    user=request.user,
                    cursor=cursor,
                    query_search=query_search
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        next_url = None

        if next_cursor:
            params = {
                'cursor': next_cursor
            }

            if query_search:
                params['q'] = query_search

            next_url = (
                f'{settings.API_BASE_URL}'
                f'/api/reports/'
                f'?{urlencode(params)}'
            )

        return Response({
            'results': ReportSerializer(
                reports, many=True
            ).data,

            'next': next_url
        })


class ReportDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]

