from django.contrib.auth.models import AbstractUser
from django.db import models, transaction, IntegrityError

from api.common.utils.entity_code import generate_entity_code

class User(AbstractUser):
    class UserRole(models.TextChoices):
        ADMIN = "admin", "admin"
        TECHNICIAN = "technician", "technician"
        FACULTY = "faculty", "faculty"

    
    user_code = models.CharField(max_length=20, unique=True)
    # first and last name are default with django
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.FACULTY)
    profile_image = models.ImageField(upload_to="users/", null=True, blank=True)
    # status is built-in django (is_active)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.user_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():
                        self.user_code = generate_entity_code(
                            model=User,
                            field_name="user_code",
                            prefix="US"
                        )

                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.user_code = None
            raise IntegrityError("Failed to generate unique user code")
