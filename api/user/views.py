from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, UpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api.user.models import User
from api.user.serializers import UserSerializer, CustomTokenObtainPairSerializer, UserUpdatePasswordSerializer, UserMinimalSerializer
from api.user.services import UserService
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,AllowAny
from api.permissions import IsAdmin, IsProfileOwner
from rest_framework.exceptions import PermissionDenied
from api.throttle import LoginThrottle
from rest_framework.views import APIView
from api.user.serializers import ForgotPasswordSerializer


from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]
    serializer_class = CustomTokenObtainPairSerializer

class UserListCreateView(ListCreateAPIView):
    serializer_class = UserSerializer

    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return UserService.get_all(
            role=self.request.query_params.get('role'),
            is_active=self.request.query_params.get('is-active')
        )

class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include"] = self.request.query_params.get("include", "")
        return context

    def retrieve(self, request, *args, **kwargs):
        profile, stats = UserService.get_profile_stats(
            request.user,
            include=request.query_params.get("include", "")
        )
        serializer = self.get_serializer(profile)

        data = serializer.data
        data["stats"] = stats

        return Response(data)
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]
        
        return [IsAuthenticated(), (IsAdmin | IsProfileOwner)()]

    
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
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK
        )

class AvailableCustodianListView(ListAPIView):
    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated, IsAdmin];

    def get_queryset(self):

        include = self.request.query_params.get('include')

        queryset = User.objects.filter(
                custodian__isnull=True,
                role='faculty'
        )

        if include:
            queryset = (
                queryset
                | User.objects.filter(id=include, role='faculty')
            ).distinct()

        return  queryset
    

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.send_reset_email(serializer.user)

        return Response(
            {
                "message": "Password reset email has been sent."
            },
            status=status.HTTP_200_OK
        )