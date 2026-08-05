from django.urls import path
from api.audit_logs.views import AuditLogsListView
urlpatterns = [
    path('', AuditLogsListView.as_view())
]