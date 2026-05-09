from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.ticket.models import Ticket
from api.ticket.serializers import TicketSerializer

class TicketListCreateView(ListCreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

class TicketDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer