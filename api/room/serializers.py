from rest_framework import serializers
from api.room.models import Room
from api.user.serializers import UserMinimalSerializer
from api.computer.models import Computer

class ComputerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = '__all__'

class RoomReadSerializer(serializers.ModelSerializer):

    computer_count = serializers.IntegerField(read_only=True)
    computer_count_with_active_issues = serializers.IntegerField(read_only=True)
    assigned_custodian = UserMinimalSerializer(read_only=True)
    computers = ComputerListSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()

        include = self.context.get("include", "")
        includes = include.split(",")

        if "computers" not in includes:
            fields.pop("computers", None)

        return fields

class RoomWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class RoomAndComputerListSerializer(serializers.ModelSerializer):
    total_computer = serializers.IntegerField(read_only=True)
    computers = ComputerListSerializer(many=True, read_only=True)
    assigned_custodian = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'assigned_custodian', 'total_computer', 'computers', 'building_name', 'floor_number']
    
class RoomMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'room_name', 'building_name', 'floor_number']


