from django.db import models
from django.conf import settings

class UserPushToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_tokens')
    expo_push_token = models.CharField(max_length=255, unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"{self.user.username} - {self.expo_push_token[:15]}"