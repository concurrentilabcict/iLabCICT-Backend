
from rest_framework import serializers
from api.notification.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Notification
        fields = '__all__'