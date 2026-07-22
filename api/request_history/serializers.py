from rest_framework import serializers
from api.request_history.models import RequestHistory
class RequestHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = RequestHistory
        fields='__all__'