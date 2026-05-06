from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.user.models import User
from api.user.serializers import UserSerializer

from rest_framework_simplejwt.views import TokenObtainPairView

class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer