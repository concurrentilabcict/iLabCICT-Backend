from django.urls import path, include
from rest_framework_simplejwt.views import (TokenObtainPairView ,TokenRefreshView)

from api.user.views import CustomTokenObtainPairView

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path('users/', include('api.user.urls')),

    path('rooms/', include('api.room.urls')),

    path('tickets/', include('api.ticket.urls')),

    path('computers/', include('api.computer.urls')),

    path('repair-logs/', include('api.repair_log.urls')),

    path('reports/', include('api.report.urls')),

    path('maintenance-history/', include('api.maintenance_history.urls')),

    path('chat/', include('api.chatbot.urls'))
]
