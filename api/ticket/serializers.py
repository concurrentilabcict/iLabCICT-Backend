from rest_framework import serializers
from api.ticket.models import Ticket
from api.computer.serializers import ComputerMinimalSerializer
from api.room.serializers import RoomMinimalSerializer
from api.user.serializers import UserMinimalSerializer

class TicketReadSerializer(serializers.ModelSerializer):
    ticket_code = serializers.CharField(read_only=True)

    reported_by = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    room = RoomMinimalSerializer(read_only=True)
    computer = ComputerMinimalSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = '__all__'

class TicketWriteSerializer(serializers.ModelSerializer):
    ticket_code = serializers.CharField(read_only=True)

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields=['reported_by', 'assigned_to']

    def create(self, validated_data):
        user = self.context["request"].user
        
        validated_data.pop("status", None)

        return Ticket.objects.create(
            reported_by=user,
            status=Ticket.TicketStatus.OPEN,
            **validated_data
        )

    def update(self, instance, validated_data):
        user = self.context["request"].user
        instance.status = validated_data.get('status', instance.status)
        instance.assigned_to = user
        instance.save()
        return instance

    def validate(self, attrs):
        request = self.context.get('request')

        if request and request.method == 'PATCH':
            invalid_fields = set(attrs.keys()) - {'status', 'assigned_to'}
            if invalid_fields:
                raise serializers.ValidationError("Only 'status' and 'assigned_to' field can be updated")

            new_status = attrs.get('status')
            current_status = self.instance.status
            computer = attrs.get('computer')
            ticket_type = attrs.get('type')
            current_ticket_type = self.instance.type
            current_assigned_to = self.instance.assigned_to
            new_assigned_to = request.user

            print(new_assigned_to)
            print(current_assigned_to)

            if (
                current_assigned_to is not None
                and new_assigned_to is not None
                and current_assigned_to != new_assigned_to
            ):
                raise serializers.ValidationError(
                    "This ticket is already assigned to another technician."
                )

            if computer is not None and ticket_type == Ticket.TicketType.REQUEST:
                raise serializers.ValidationError('Request ticket cannot contain computer data')

            if current_status == Ticket.TicketStatus.RESOLVED:
                raise serializers.ValidationError('Completed Tickets cannot be modified')
            elif current_status == Ticket.TicketStatus.ONGOING and new_status == Ticket.TicketStatus.OPEN:
                raise serializers.ValidationError('Ongoing tickets cannot be reverted to Open.')
            elif new_status == Ticket.TicketStatus.RESOLVED and current_ticket_type == Ticket.TicketType.REPORT:
                raise serializers.ValidationError('Report Tickets cannot be completed manually')

        return attrs
    
class MinimalTicketSerializer(serializers.ModelSerializer):

    reported_by = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    class Meta:
        model = Ticket
        fields = ['id', 'type', 'reported_by', 'title', 'assigned_to']

class NotificationTicketSerializer(serializers.ModelSerializer):

    reported_by = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    class Meta:
        model = Ticket
        fields = ['id', 'type', 'reported_by', 'title', 'assigned_to']

class MaintenanceHistoryTicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = ['id', 'status', 'issue_image']