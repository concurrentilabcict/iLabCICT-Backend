from rest_framework import serializers
from api.task_scheduler.models import TaskScheduler
class TaskSchedulerSerializer(serializers.ModelSerializer):

    class Meta:
        model=TaskScheduler
        fields='__all__'
        