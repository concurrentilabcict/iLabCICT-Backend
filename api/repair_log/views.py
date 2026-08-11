from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogReadSerializer, RepairLogWriteSerializer, RepairLogDetailSerializer, MainRepairLogReadSerializer
from api.repair_log.services import RepairLogService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician
from django.conf import settings
from rest_framework.response import Response
class RepairLogListCreateView(ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTechnician()]
        
        return [IsAuthenticated(), (IsAdmin | IsTechnician)()]

    def get(self, request, *args, **kwargs):
        cursor = self.request.query_params.get('cursor')

        try:
            repair_log, next_cursor = (
                RepairLogService.get_paginated_repair_logs(
                    user=request.user,
                    cursor=cursor
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        return Response({
            'results': MainRepairLogReadSerializer(
                repair_log, many=True
            ).data,
            'next': (
                f'{settings.API_BASE_URL}'
                f'/api/repair-logs/'
                f'?cursor={next_cursor}'
                if next_cursor
                else None
            )
        })

    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RepairLogWriteSerializer
        
        return MainRepairLogReadSerializer
    
class RepairLogDetailView(RetrieveAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogDetailSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]
    
