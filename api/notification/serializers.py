
from rest_framework import serializers
from api.notification.models import Notification

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