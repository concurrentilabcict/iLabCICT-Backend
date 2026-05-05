from rest_framework import serializers
from api.peripheral.model import Peripheral

class PeripheralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Peripheral
        fields = '__all__'