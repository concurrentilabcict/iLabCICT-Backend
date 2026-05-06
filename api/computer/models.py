from django.db import models
from api.computer.models import Computer

class Computer(models.Model):
    room = models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='rooms')
    