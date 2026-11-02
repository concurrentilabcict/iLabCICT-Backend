from django.urls import path
from .views import ProcessView, StatusView

app_name = "replication"
urlpatterns = [
    path("process/", ProcessView.as_view(), name="process"),
    path("status/", StatusView.as_view(), name="status"),
]
