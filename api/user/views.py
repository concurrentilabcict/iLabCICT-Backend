from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api.user.models import User
from api.user.serializers import UserSerializer, CustomTokenObtainPairSerializer
from api.user.services import UserService

from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    parser_classes = [JSONParser, MultiPartParser, FormParser]

class UserRoleListView(ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        role = self.request.query_params.get("role")
        return UserService.get_all_by_role(role)