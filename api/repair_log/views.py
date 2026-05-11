from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.repair_log.models import RepairLog
from api.repair_log.serializers import RepairLogSerializer

class RepairLogListCreate(ListCreateAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer

class RepairLogDetail(RetrieveUpdateDestroyAPIView):
    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer