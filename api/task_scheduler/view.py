from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView
from rest_framework.views import APIView
from api.task_scheduler.models import TaskScheduler
from api.task_scheduler.serializer import TaskSchedulerSerializer
from api.permissions import IsAdmin
from rest_framework.permissions import IsAuthenticated

class CreateTaskSchedulerView(CreateAPIView):
    serializer_class=TaskSchedulerSerializer
    queryset=TaskScheduler.objects.all()
    permission_classes= [IsAuthenticated, IsAdmin]

class TaskSchedulerDetailView(RetrieveUpdateAPIView):
    serializer_class=TaskSchedulerSerializer
    queryset = TaskScheduler.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

class SchedulerView(APIView):
    permission_classes=[]
    ...
        

