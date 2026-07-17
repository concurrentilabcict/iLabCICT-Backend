from django.urls import path, include, re_path
from rest_framework_simplejwt.views import (TokenObtainPairView ,TokenRefreshView)

from api.user.views import CustomTokenObtainPairView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

schema_view = get_schema_view(
    openapi.Info(
        title="iLabCICT API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
    permission_classes=(AllowAny,)
)


class PingView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"ok": True})


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

    path('ping/', PingView.as_view())
]
