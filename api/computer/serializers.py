from rest_framework import serializers
from api.computer.models import Computer

class ComputerSerializer(serializers.ModelSerializer):
    computer_code = serializers.CharField(read_only=True)
    class Meta:
        model = Computer
        fields = '__all__'


class ComputerMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = ['id', 'computer_code']