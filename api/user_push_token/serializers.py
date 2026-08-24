from rest_framework import serializers
class UserPushTokenSerializer(serializers.Serializer):
    expo_push_token = serializers.CharField(max_length=255)

    def validate_push_token(self, value):
        if not value.startswith("ExponentPushToken["):
            raise serializers.ValidationError("Invalid Expo Push Token.")
        return value