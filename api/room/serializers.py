from rest_framework import serializers
from api.room.models import Room
from api.user.serializers import UserMinimalSerializer

class RoomSerializer(serializers.ModelSerializer):

    computer_count = serializers.SerializerMethodField()
    assigned_custodian = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Room
        fields = '__all__'

    def get_computer_count(self, obj):
        return obj.computers.count()
    
class RoomMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'room_name', 'building_name']