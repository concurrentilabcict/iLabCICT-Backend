from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from api.user.models import User
from api.user.serializers import UserSerializer

class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer