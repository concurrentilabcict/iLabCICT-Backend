from django.db import models

class TaskScheduler(models.Model):

    class FrequencyValues(models.TextChoices):
        ONCE = 'once', 'once'
        DAILY = 'daily', 'daily'
        WEEKLY = 'weekly', 'weekly'
        MONTHLY = 'monthly', 'monthly'
    
    type = models.CharField(max_length=20)
    enabled = models.BooleanField(default=True)
    frequency = models.CharField(max_length=20, choices=FrequencyValues, default=FrequencyValues.WEEKLY)
    weekday = models.IntegerField(null=True, blank=True)
    execution_time = models.TimeField(null=True)
    next_execution = models.DateTimeField(null=True)
    last_execution = models.DateTimeField(null=True, blank=True)

