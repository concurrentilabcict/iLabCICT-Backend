from rest_framework import serializers
from api.ticket.models import Ticket
from api.computer.serializers import ComputerMinimalSerializer
from api.room.serializers import RoomMinimalSerializer
from api.user.serializers import UserMinimalSerializer
class TicketSerializer(serializers.ModelSerializer):
    ticket_code = serializers.CharField(read_only=True)

    reported_by = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    room = RoomMinimalSerializer(read_only=True)
    computer = ComputerMinimalSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = '__all__'