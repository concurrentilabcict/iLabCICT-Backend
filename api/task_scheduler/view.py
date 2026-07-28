from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView
from rest_framework.views import APIView
from api.task_scheduler.models import TaskScheduler
from api.task_scheduler.services import TaskSchedulerService
from api.task_scheduler.serializer import TaskSchedulerSerializer
from api.permissions import IsAdmin, HasSchedulerToken
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class CreateTaskSchedulerView(CreateAPIView):
    serializer_class=TaskSchedulerSerializer
    queryset=TaskScheduler.objects.all()
    permission_classes= [IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        TaskSchedulerService.create_schedule(serializer=serializer)

class TaskSchedulerDetailView(RetrieveUpdateAPIView):
    serializer_class=TaskSchedulerSerializer
    queryset = TaskScheduler.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_update(self, serializer):
        TaskSchedulerService.update_schedule(serializer=serializer)

class SchedulerView(APIView):
    authentication_classes = []
    permission_classes=[HasSchedulerToken]

    def get(self, request):
        res = TaskSchedulerService.execute_task()

        return Response(
            {
                "detail": "Scheduler executed successfully",
                "message": res
             }
        )

        
        

