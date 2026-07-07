from rest_framework import serializers
from api.computer.models import Computer
from api.room.serializers import RoomMinimalSerializer
from rest_framework.exceptions import ValidationError
from django.db import transaction

class ComputerWriteSerializer(serializers.ModelSerializer):
    computer_code = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(write_only=True)

    class Meta:
        model = Computer
        fields = '__all__'

    def validate(self, attrs):
        if self.instance is None:
            quantity = attrs['quantity']

            if quantity is None:
                raise ValidationError('Quantity is required')
            if quantity < 1:
                raise ValidationError('Quantity must be greater than 0')

        return attrs
        
    def create(self, validated_data):
        quantity = validated_data.pop('quantity')
        
        with transaction.atomic():
            computers = []

            for _ in range(quantity):
                computer = Computer(**validated_data)
                computer.save()
                computers.append(computer)

        return computers


class ComputerReadSerializer(serializers.ModelSerializer):
    room = RoomMinimalSerializer(read_only=True)

    class Meta:
        model = Computer
        fields = '__all__'

class ComputerMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = ['id', 'computer_code']

class ComputerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = ['id', 'computer_code', 'operating_system', 'computer_status']