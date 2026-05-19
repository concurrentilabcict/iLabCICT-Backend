from django.urls import path
from api.maintenance_history.views import MaintenanceHistoryListCreateView, MaintenanceHistoryByComputerCode, MaintenanceHistoryDetailView

urlpatterns = [
    path('', MaintenanceHistoryListCreateView.as_view()),
    path('<int:pk>/', MaintenanceHistoryDetailView.as_view()),

    path('computer/', MaintenanceHistoryByComputerCode.as_view()),
]