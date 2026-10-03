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

class ReportAssingmentSerializer(serializers.ModelSerializer):

    technician_id = serializers.IntegerField()
    month_date = serializers.IntegerField()
    class Meta:
        model = Report
        fields = ['technician_id','month_date']