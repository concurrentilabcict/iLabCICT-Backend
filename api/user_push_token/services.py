from api.user_push_token.models import UserPushToken

class UserPushTokenService:

    @staticmethod
    def register_push_token(user, push_token):
        UserPushToken.objects.update_or_create(
            expo_push_token=push_token,
            defaults={
                'user': user
            }
        )

    @staticmethod
    def get_push_tokens(user):
        return UserPushToken.objects.filter(user=user)