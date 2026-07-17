from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView, RetrieveAPIView
from api.computer.models import Computer
from api.computer.serializers import ComputerReadSerializer, ComputerWriteSerializer
from api.computer.services import ComputerService
from api.permissions import IsAdmin, IsTechnician, IsStaff
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

class ComputerListCreateView(ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ComputerWriteSerializer

        return ComputerReadSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), (IsAdmin | IsTechnician)()]
        
        return [IsAuthenticated(), IsStaff()]
    #new
    def get_queryset(self):
        return ComputerService.get_all(filters=self.request.query_params)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        computers = serializer.save()

        output = ComputerReadSerializer(computers, many=True)
        return Response(output.data, status=status.HTTP_201_CREATED)

class ComputerDetailView(RetrieveUpdateDestroyAPIView):

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return ComputerWriteSerializer

        return ComputerReadSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]
        elif self.request.method in ('PATCH', 'PUT'):
            return [IsAuthenticated(), (IsAdmin | IsTechnician)()]
        
        return [IsAuthenticated(), IsStaff()]

class ComputerCodeDetailView(RetrieveAPIView):

    lookup_field = 'computer_code'
    lookup_url_kwarg ='uk'

    def get_queryset(self):
        computer_code = self.kwargs['uk']
        return ComputerService.get_computer_with_mainentance_history(
            include=self.request.query_params.get("include", ""),
            computer_code=computer_code
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include"] = self.request.query_params.get("include", "")
        return context

    serializer_class = ComputerReadSerializer

    permission_classes = [IsAuthenticated, IsStaff]

#old one
class ActiveComputerListView(ListAPIView):
    serializer_class = ComputerReadSerializer

    def get_queryset(self):
        return ComputerService.get_all_active()
    
class ActiveComputerWithActivePeripheralsListView(ListAPIView):
    serializer_class = ComputerReadSerializer

    def get_queryset(self):
        return ComputerService.get_all_with_active_peripherals()
    
class ActiveComputerWithPeripheralListView(ListAPIView):
    serializer_class = ComputerReadSerializer

    def get_queryset(self):
        filters = self.request.query_params
        return ComputerService.get_all_active_with_peripheral(filters=filters)
    
class ActiveComputerNoPeripheralsView(ListAPIView):
    serializer_class = ComputerReadSerializer

    def get_queryset(self):
        return ComputerService.get_all_active_no_peripherals()