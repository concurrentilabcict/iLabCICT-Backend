from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogSerializer

class RepairLogListCreateView(ListCreateAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer

class RepairLogDetailView(RetrieveUpdateDestroyAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer