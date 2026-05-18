from django.urls import path
from api.report.views import ReportByTechnicianListView, ReportDetailView, ReportListCreateView

urlpatterns = [
    path('', ReportListCreateView.as_view()),
    path('<int: pk>/', ReportDetailView.as_view()),

    path('technician/', ReportByTechnicianListView.as_view())
]