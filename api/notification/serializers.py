
from rest_framework import serializers
from api.notification.models import Notification
from api.ticket.serializers import NotificationTicketSerializer
from api.report.serializers import NotificationReportSerializer

class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    
    class Meta: 
        model = Notification
        fields = [
            'id',
            'recipient_id',
            'entity_id',
            'entity_type',
            'event_type',
            'title',
            'activity_summary',
            'status',
            'is_archived',
            'created_at',
            'is_read',
        ]

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance
    
    def validate(self, attrs):
        request = self.context.get('request')

        if request and request.method == 'PATCH':
            invalid_fields = set(attrs.keys()) - {'status'}
            if invalid_fields:
                raise serializers.ValidationError("Only 'status' field can be updated.")

        return attrs

    def get_is_read(self, obj):
        request = self.context.get("request")

        if request:
            user = request.user
        else:
            user = self.context.get("user")

        if not user or not user.is_authenticated:
            return False

        return user.id in obj.read_by




    