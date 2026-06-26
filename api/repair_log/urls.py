from django.urls import path
from api.repair_log.views import RepairLogListCreateView, RepairLogDetailView

urlpatterns = [
    path('', RepairLogListCreateView.as_view()),
    path('<int:pk>/', RepairLogDetailView.as_view()),
]
