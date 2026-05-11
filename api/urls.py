from django.urls import path, include
from rest_framework_simplejwt.views import (TokenObtainPairView ,TokenRefreshView)

urlpatterns = [
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path('users/', include('api.user.urls')),

    path('rooms/', include('api.room.urls')),

    path('tickets/', include('api.ticket.urls')),

    path('computers/', include('api.computer.urls')),

    path('repair-logs/', include('api.repair_logs.urls'))
]
