from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class UserRole(models.TextChoices):
        ADMIN = "admin", "admin"
        TECHNICIAN = "technician", "technician"
        FACULTY = "faculty", "faculty"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.FACULTY)
    profile_image = models.ImageField(upload_to="users/", null=True, blank=True)
    # status is built-in django (is_active)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)