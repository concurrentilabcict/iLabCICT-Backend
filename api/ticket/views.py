from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.ticket.models import Ticket
from api.ticket.serializers import TicketSerializer
from api.ticket.services import TicketService

class TicketListCreateView(ListCreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

class TicketDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

class TicketStatusListView(ListAPIView):
    serializer_class = TicketSerializer

    def get_queryset(self):
        status = self.request.query_params.get("status")
        return TicketService.get_all_by_status(status)