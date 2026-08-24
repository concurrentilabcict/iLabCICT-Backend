from rest_framework import serializers
from api.user_push_token.models import UserPushToken
class UserPushTokenSerializer(serializers.Serializer):
    expo_push_token = serializers.CharField(max_length=255)

    def validate_push_token(self, value):
        if not value.startswith("ExponentPushToken["):
            raise serializers.ValidationError("Invalid Expo Push Token.")
        return value

    class Meta:
        model = UserPushToken
        fields = [
            "id",
            "expo_push_token",
            "updated_at",
            "created_at"
        ]