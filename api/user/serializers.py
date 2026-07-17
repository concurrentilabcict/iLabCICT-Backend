from rest_framework import serializers
from api.user.models import User
from django.contrib.auth import authenticate
from api.user.services import UserService

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
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
       
        if password:
            raise serializers.ValidationError('Password not authorized to be updated.')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
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
        data["email"] = self.user.email
        data["is_authenticated"] = self.user.is_authenticated
        data["is_active"] = self.user.is_active
        data["profile_image"] = profile_image.url if profile_image else None

        return data
    
class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'last_name', 'first_name']

class UserUpdatePasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    old_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['password', 'old_password']

    def update(self, instance, validated_data):
        old_password = validated_data.pop("old_password", None)
        new_password = validated_data.pop("password", None)

        if not instance.check_password(old_password):
            raise serializers.ValidationError('Incorrect password.')
        
        instance.set_password(new_password)
        instance.save()
        return instance
