
from rest_framework import serializers
from api.notification.models import Notification
from api.ticket.serializers import NotificationTicketSerializer
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
                raise serializers.ValidationError({
                    'message': f"Only 'status' field can be updated."
                })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.type == 'ticket':
            data['ticket'] = NotificationTicketSerializer(instance.ticket).data
            data.pop('report', None)
        
        return data
    



    