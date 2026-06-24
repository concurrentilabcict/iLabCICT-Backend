from rest_framework import serializers
from api.report.models import Report
from api.user.serializers import UserMinimalSerializer
class ReportSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Report
        fields = '__all__'

class NotificationReportSerializer(serializers.ModelSerializer):

    technician = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Report
        fields = ['technician','title']