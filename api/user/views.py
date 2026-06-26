from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api.user.models import User
from api.user.serializers import UserSerializer, CustomTokenObtainPairSerializer, UserUpdatePasswordSerializer
from api.user.services import UserService
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserListCreateView(ListCreateAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        return UserService.get_all(
            role=self.request.query_params.get('role'),
            is_active=self.request.query_params.get('is-active')
        )

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    
class UserUpdatePassword(UpdateAPIView):
    serializer_class = UserUpdatePasswordSerializer
    http_method_names = ['patch']
    queryset = User.objects.all()

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK
        )