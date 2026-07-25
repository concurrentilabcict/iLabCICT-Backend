from django.urls import path
from api.task_scheduler.view import TaskSchedulerDetailView, CreateTaskSchedulerView, SchedulerView
urlpatterns = [
    path('', CreateTaskSchedulerView.as_view()),
    path('<int:pk>/', TaskSchedulerDetailView.as_view()),
    path('reports/', SchedulerView.as_view())
]