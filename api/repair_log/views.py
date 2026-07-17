from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogReadSerializer, RepairLogWriteSerializer, RepairLogDetailSerializer, MainRepairLogReadSerializer
from api.repair_log.services import RepairLogService
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsAdmin, IsTechnician

class RepairLogListCreateView(ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTechnician()]
        
        return [IsAuthenticated(), (IsAdmin | IsTechnician)()]

    def get_queryset(self):
        return RepairLogService.get_all(
            user=self.request.user,
            technician_id=self.request.query_params.get('technician-id'),
            date=self.request.query_params.get('date')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RepairLogWriteSerializer
        
        return MainRepairLogReadSerializer
    
class RepairLogDetailView(RetrieveAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogDetailSerializer

    permission_classes = [IsAuthenticated, IsAdmin | IsTechnician]
    
