
from django.urls import path
from api.notification.views import NotificationDetailView, NotificationListView, NotificationReadView

urlpatterns=[
    path('user/', NotificationListView.as_view()),
    path('<int:pk>/', NotificationDetailView.as_view()),
    path('<int:pk>/read/', NotificationReadView.as_view())
]