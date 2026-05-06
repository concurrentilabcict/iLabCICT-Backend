from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from api.user.jwt import CustomTokenObtainPairSerializer

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairSerializer.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path('user/', include('api.user.urls'))
]
