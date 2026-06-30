
from rest_framework import serializers
from api.notification.models import Notification
from api.ticket.serializers import NotificationTicketSerializer
from api.report.serializers import NotificationReportSerializer
class NotificationSerializer(serializers.ModelSerializer):
    
    class Meta: 
        model = Notification
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
                raise serializers.ValidationError("Only 'status' field can be updated.")

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.type == Notification.NotificationTypes.TICKET:
            data['ticket'] = NotificationTicketSerializer(instance.ticket).data
            data.pop('report', None)
        elif instance.type == Notification.NotificationTypes.REPORT:
            data['report'] = NotificationReportSerializer(instance.report).data
            data.pop('ticket', None)
                    
        return data
    



    