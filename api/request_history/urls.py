from django.urls import path
from api.request_history.views import RequestHistoryListView, RequestHistoryDetailView

urlpatterns = [
    path('', RequestHistoryListView.as_view()),
    path('<int:pk>/', RequestHistoryDetailView.as_view()),
]