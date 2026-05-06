from django.db import models

class Room(models.Model):
    room_name = models.CharField(max_length=20)
    floor_number = models.IntegerField()
    computer_count = models.IntegerField()
    status = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)