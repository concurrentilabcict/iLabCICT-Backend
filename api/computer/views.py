from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.computer.models import Computer
from api.computer.serializers import ComputerSerializer
from api.computer.services import ComputerService

class ComputerListCreateView(ListCreateAPIView):
    serializer_class = ComputerSerializer

    #new
    def get_queryset(self):
        return ComputerService.get_all(filters=self.request.query_params)

class ComputerDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer

#old one
class ActiveComputerListView(ListAPIView):
    serializer_class = ComputerSerializer

    def get_queryset(self):
        return ComputerService.get_all_active()
    
class ActiveComputerWithActivePeripheralsListView(ListAPIView):
    serializer_class = ComputerSerializer

    def get_queryset(self):
        return ComputerService.get_all_with_active_peripherals()
    
class ActiveComputerWithPeripheralListView(ListAPIView):
    serializer_class = ComputerSerializer

    def get_queryset(self):
        filters = self.request.query_params
        return ComputerService.get_all_active_with_peripheral(filters=filters)
    
class ActiveComputerNoPeripheralsView(ListAPIView):
    serializer_class = ComputerSerializer

    def get_queryset(self):
        return ComputerService.get_all_active_no_peripherals()