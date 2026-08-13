from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogReadSerializer, RepairLogWriteSerializer, RepairLogDetailSerializer, MainRepairLogReadSerializer
from api.repair_log.services import RepairLogService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician
from django.conf import settings
from rest_framework.response import Response
from urllib.parse import urlencode
class RepairLogListCreateView(ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTechnician()]
        
        return [IsAuthenticated(), (IsAdmin | IsTechnician)()]

    def get(self, request, *args, **kwargs):
        cursor = self.request.query_params.get('cursor')
        query_search= self.request.query_params.get('q')
        date = self.request.query_params.get('date')
        technician_id = self.request.query_params.get('technician_id')

        try:
            repair_log, next_cursor = (
                RepairLogService.get_paginated_repair_logs(
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

            if date:
                params['date'] = date

            
            if technician_id:
                params['technician_id'] = technician_id

            next_url = (f'{settings.API_BASE_URL}'
                        f'/api/repair-logs/'
                        f'?{urlencode(params)}')

        return Response({
            'results': MainRepairLogReadSerializer(
                repair_log, many=True
            ).data,
            'next': next_url
        })

    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RepairLogWriteSerializer
        
        return MainRepairLogReadSerializer
    
class RepairLogDetailView(RetrieveAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogDetailSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]
    
