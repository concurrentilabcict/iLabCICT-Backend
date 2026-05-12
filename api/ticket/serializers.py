from rest_framework import serializers
from api.ticket.models import Ticket

class TicketSerializer(serializers.ModelSerializer):
    ticket_code = serializers.CharField(read_only=True)
    class Meta:
        model = Ticket
        fields = '__all__'