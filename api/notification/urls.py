
from django.urls import path
from api.notification.views import NotificationDetailView, NotificationListView

urlpatterns=[
    path('user/', NotificationListView.as_view()),
    path('<int:pk>/', NotificationDetailView.as_view())
]