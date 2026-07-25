from django.urls import path
from api.task_scheduler.view import TaskSchedulerDetailView
urlpatterns = [
    path('<int:pk>/', TaskSchedulerDetailView.as_view())
]