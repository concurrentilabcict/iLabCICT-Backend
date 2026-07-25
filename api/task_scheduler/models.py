from django.db import models

class TaskScheduler(models.Model):
    type = models.CharField(max_length=20)
    scheduled_execution = models.DateTimeField()
    enabled = models.BooleanField()
    