from rest_framework import serializers
from api.request_history.models import RequestHistory
from api.room.serializers import RoomMinimalSerializer
from api.ticket.serializers import RequestHistoryTicketSerializer
from api.user.serializers import UserMinimalSerializer
class RequestHistorySerializer(serializers.ModelSerializer):

    room = RoomMinimalSerializer()
    ticket = RequestHistoryTicketSerializer()
    technician = UserMinimalSerializer()

    class Meta:
        model = RequestHistory
        fields='__all__'