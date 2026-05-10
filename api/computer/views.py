from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.computer.models import Computer
from api.computer.serializers import ComputerSerializer

class ComputerListCreateView(ListCreateAPIView):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer

class ComputerDetail(RetrieveUpdateDestroyAPIView):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer