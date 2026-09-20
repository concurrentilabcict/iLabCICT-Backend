from django.db import models
from api.user.models import User
class PrintableTemplate(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )

    template_url = models.URLField()

    is_active = models.BooleanField(default=True)

    cloudinary_public_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    updated_at = models.DateTimeField(auto_now=True)

    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
