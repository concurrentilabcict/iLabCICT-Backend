from django.db import models

class Peripheral(models.Model):
    peripheral_code = models.CharField(max_length=30, unique=True)
    brand = models.CharField(max_length=20)
    model = models.CharField(max_length=20)
    device_type = models.CharField(max_length=20)
    status = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

