from rest_framework import serializers
from api.user.models import User

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    user_code = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "user_code",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "profile_image",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
         token = super().get_token(user)
         
         token["first_name"] = user.first_name
         token["last_name"] = user.last_name
         token["role"] = user.role

         return token
    
    def validate(self, attrs):
        data = super().validate(attrs)

        profile_image = self.user.profile_image

        data["role"] = self.user.role
        data["id"] = self.user.id
        data["first_name"] = self.user.first_name
        data["last_name"] = self.user.last_name
        data["is_authenticated"] = self.user.is_authenticated
        data["is_active"] = self.user.is_active
        data["profile_image"] = profile_image.url if profile_image else None

        return data