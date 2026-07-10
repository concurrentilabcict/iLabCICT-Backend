from django.urls import path, include, re_path
from rest_framework_simplejwt.views import (TokenObtainPairView ,TokenRefreshView)

from api.user.views import CustomTokenObtainPairView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from api.permissions import IsStaff
from rest_framework.permissions import IsAuthenticated

schema_view = get_schema_view(
    openapi.Info(
        title="iLabCICT API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
)


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

    path('chat/', include('api.chatbot.urls')),

    path('notifications/', include('api.notification.urls')),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
