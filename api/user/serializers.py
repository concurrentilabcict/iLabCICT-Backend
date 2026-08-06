from rest_framework import serializers
from api.user.models import User
from django.contrib.auth import authenticate
from api.user.services import UserService
from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta
from rest_framework_simplejwt.exceptions import TokenError
from api.audit_logs.models import AuditLogs
from api.audit_logs.services import AuditLogsService
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
        request = self.context['request']
        user_name = request.user.get_full_name()
       
        if password:
            AuditLogs.objects.create(
                performed_by=request.user,
                action_title='Unauthorized change password attempt',
                action_summary= f'{user_name} attempted to updated their password using the profile update endpoint.',
                metadata={
                    'result': 'blocked',
                    'field': 'password',
                    'endpoint': request.path,
                    'ip_address': AuditLogsService.get_ip_address(request),
                    'user_agent': AuditLogsService.get_user_agent(request)

                }
            )

            raise serializers.ValidationError('Password not authorized to be updated.')

        changes = {}

        for field in ['first_name', 'last_name', 'email', 'profile_image']:
            if field not in validated_data:
                continue

            if field == "profile_image":
                old_value = instance.profile_image.name if instance.profile_image else None
                new_value = validated_data[field].name if validated_data[field] else None

                if old_value != new_value:
                    changes[field] = {
                        "changed": True
                    }

                continue

            old_value = getattr(instance, field)
            new_value = validated_data[field]

            if old_value != new_value:
                changes[field] = {
                    "old": old_value,
                    "new": new_value,
                }

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()

        if changes:
            AuditLogs.objects.create(
                performed_by=request.user,
                action_title='Updated user profile',
                action_summary= f'{user_name} updated their profile information.',
                metadata={
                    'result': 'successful',
                    'changes': changes,
                    'ip_address': AuditLogsService.get_ip_address(request),
                    'user_agent': AuditLogsService.get_user_agent(request)
                }
            )

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
        
        request = self.context['request']

        try:
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

            
        except serializers.ValidationError:
            AuditLogs.objects.create(
                performed_by=None,
                action_tile='Failed login attempt',
                action_summary=f'Someone attempted to log in using: {attrs.get('username')}',
                metadata={
                    'result': 'blocked',
                    'ip_address': AuditLogsService.get_client_ip(request),
                    'user_agent': AuditLogsService.get_user_agent(request)
                }
            )
            raise

        AuditLogs.objects.create(
                    performed_by=self.user,
                    action_title='User Login',
                    action_summary=f'{self.user.get_full_name()} logged in.',
                    metadata={
                        'result': 'successful',
                        'ip_address': AuditLogsService.get_client_ip(request),
                        'user_agent': AuditLogsService.get_user_agent(request)
                    }
                )

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

        request = self.context["request"]
        if not instance.check_password(old_password):

            AuditLogs.objects.create(
                performed_by=instance,
                action_title='Failed attempt to change user password',
                action_summary=f"{instance.get_full_name()} entered an incorrect password.",
                metadata={
                    'result': 'unsuccessful',
                    'ip_address': AuditLogsService.get_client_ip(request),
                    'user_agent': AuditLogsService.get_user_agent(request)
                }
            )

            raise serializers.ValidationError('Incorrect password.')

        instance.set_password(new_password)
        instance.save(update_fields=['password'])

        AuditLogs.objects.create(
            performed_by=instance,
            action_title="Password Changed",
            action_summary=f"{instance.get_full_name()} changed their password.",
            metadata={
                "result": "successful",
                "ip_address": AuditLogsService.get_client_ip(request),
                "user_agent": AuditLogsService.get_user_agent(request),
            },
        )

        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = User.objects.filter(
            email=value,
            is_active=True
        ).first()

        request = self.context['request']

        if not user:
            AuditLogs.objects.create(
                performed_by=None,
                action_title='Invalid password reset attempt',
                action_summary=f"Password reset requested for an unknown or inactive account: {value}.",
                metadata={
                    'result': 'unsuccessful',
                    'email': value,
                    'ip_address': AuditLogsService.get_client_ip(request),
                    'user_agent': AuditLogsService.get_user_agent(request),
                }
            )

            raise serializers.ValidationError(
                "No active account found."
            )

        self.user = user
        return value


    
class ResetPasswordWithTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                "Passwords do not match."
            )

        request = self.context['request']

        try:
            token = AccessToken(attrs["token"])

            if token.get("purpose") != "password_reset":

                AuditLogs.objects.create(
                    performed_by=None,
                    action_title="Failed Password Reset",
                    action_summary="Password reset attempted with an invalid reset token.",
                    metadata={
                        "result": "unsuccessful",
                        "reason": "invalid_token",
                        "ip_address": AuditLogsService.get_client_ip(request),
                        "user_agent": AuditLogsService.get_user_agent(request),
                    },
                )

                raise serializers.ValidationError(
                    "Invalid reset token."
                )

            user = User.objects.get(id=token["user_id"])

        except TokenError as e:
            AuditLogs.objects.create(
                performed_by=None,
                action_title="Failed Password Reset",
                action_summary="Token error occured on password reset attempt",
                metadata={
                    "result": "unsuccessful",
                    "reason": str(e),
                    "ip_address": AuditLogsService.get_client_ip(request),
                    "user_agent": AuditLogsService.get_user_agent(request),
                },
            )
            raise serializers.ValidationError(str(e))

        except User.DoesNotExist:
            AuditLogs.objects.create(
                performed_by=None,
                action_title="Failed Password Reset",
                action_summary="Password reset attempted with on an unknown user.",
                metadata={
                    "result": "unsuccessful",
                    "reason": "invalid_user",
                    "ip_address": AuditLogsService.get_client_ip(request),
                    "user_agent": AuditLogsService.get_user_agent(request),
                },
            )

            raise serializers.ValidationError("User does not exist.")

        attrs["user"] = user

        return attrs
