from rest_framework import serializers
from api.task_scheduler.models import TaskScheduler
class TaskSchedulerSerializer(serializers.Serializer):

    class Meta:
        model=TaskScheduler
        fields='__all__'
        