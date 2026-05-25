from rest_framework import serializers
from api.room.models import Room

class RoomSerializer(serializers.ModelSerializer):

    computer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = '__all__'

    def get_computer_count(self, obj):
        return obj.computers.count()
    
class RoomMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'room_name', 'building_name']