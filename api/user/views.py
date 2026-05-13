from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.user.models import User
from api.user.serializers import UserSerializer
from api.user.services import UserService

class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserRoleListView(ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        role = self.request.query_params.get("role")
        return UserService.get_all_by_role(role)