from django.urls import path
from api.maintenance_history.views import MaintenanceHistoryListCreateView, MaintenanceHistoryByComputerCode

urlpatterns = [
    path('', MaintenanceHistoryListCreateView.as_view()),
    path('<int:pk>/', MaintenanceHistoryListCreateView.as_view()),

    path('computer/', MaintenanceHistoryByComputerCode.as_view()),
]