from django.db import models
from api.user.models import User

class OTPCode(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_codes'
    )

    code_hash = models.CharField(max_length=128)

    reset_token_hash = models.CharField(max_length=128, null=True, blank=True)

    reset_token_expires_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(default=0)

    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    used_at = models.DateTimeField(null=True, blank=True)

    token_id = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'expires_at']),
        ]