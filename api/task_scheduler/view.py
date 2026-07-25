from rest_framework.generics import RetrieveUpdateAPIView
from api.task_scheduler.models import TaskScheduler
from api.task_scheduler.serializer import TaskSchedulerSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated 
class TaskSchedulerDetailView(RetrieveUpdateAPIView):
    serializer_class=TaskSchedulerSerializer
    queryset = TaskScheduler.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]
        

