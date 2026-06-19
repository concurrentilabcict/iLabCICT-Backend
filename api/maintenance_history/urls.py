from django.urls import path
from api.maintenance_history.views import MaintenanceHistoryListView, MaintenanceHistoryByComputerCode, MaintenanceHistoryDetailView

urlpatterns = [
    path('', MaintenanceHistoryListView.as_view()),
    path('<int:pk>/', MaintenanceHistoryDetailView.as_view()),

    path('computer/', MaintenanceHistoryByComputerCode.as_view()),
]