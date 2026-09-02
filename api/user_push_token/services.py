from api.user_push_token.models import UserPushToken
import requests
from api.user.models import User

class UserPushTokenService:

    EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'

    @staticmethod
    def send_notification_to_users(users, title, body, extra_data=None):


        if users is None:
            return False

        if isinstance(users, User):
            users = [users]

        tokens = list(
            UserPushToken.objects.filter(user__in=users)
            .values_list('expo_push_token', flat=True)
        )

        print(tokens)

        if not tokens:
            return False

        messages = [
            {
                'to': token,
                'sound': 'default',
                'title': title,
                'body': body,
                'data': extra_data or {},
                'priority': 'high',
            }
            for token in tokens
            ]

        results = []
        for i in range(0, len(messages), 100):
            chunk = messages[i:i + 100]
            try:
                response = requests.post(
                    UserPushTokenService.EXPO_PUSH_URL,
                    json=chunk,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                results.append(response.json())
                print('hello:', results)
            except Exception as e:
                print(f'Failed to send push notification batch: {e}')
                results.append(None)

        
        return results


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