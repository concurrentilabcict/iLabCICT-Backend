from django.urls import path
from api.repair_log.views import RepairLogListCreate, RepairLogDetail

urlpatterns = [
    path('', RepairLogListCreate.as_view()),
    path('<int:pk>/', RepairLogDetail.as_view())
]
