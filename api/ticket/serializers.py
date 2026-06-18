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

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance

    def validate(self, attrs):
        request = self.context.get('request')

        if request and request.method == 'PATCH':
            invalid_fields = set(attrs.keys()) - {'status'}
            if invalid_fields:
                raise serializers.ValidationError({
                    'message': f"Only 'status' field can be updated"
                })

            new_status = attrs.get('status')
            current_status = self.instance.status

            if current_status == 'resolved':
                raise serializers.ValidationError({
                    'message': f"Completed Tickets cannot be modified"
                })
            elif current_status == 'ongoing' and new_status == 'open':
                raise serializers.ValidationError({
                    'message': f"Ongoing tickets cannot be reverted to Open."
                })
            elif new_status == 'resolved':
                raise serializers.ValidationError({
                    'message': f"Tickets cannot be completed manually"
                })

        return attrs