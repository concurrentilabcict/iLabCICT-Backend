from django.urls import path
from api.report.views import ReportDetailView, ReportListCreateView, GenerateReportTest

urlpatterns = [
    path('', ReportListCreateView.as_view()),
    path('<int:pk>/', ReportDetailView.as_view()),
    path('test/', GenerateReportTest.as_view())

]