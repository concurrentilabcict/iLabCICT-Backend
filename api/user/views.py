from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, UpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api.user.models import User
from api.user.serializers import UserSerializer, CustomTokenObtainPairSerializer, UserUpdatePasswordSerializer, UserMinimalSerializer
from api.user.services import UserService
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated,AllowAny
from api.permissions import IsAdmin, IsProfileOwner
from api.throttle import LoginThrottle, ResetPasswordThrottle
from rest_framework.views import APIView
from api.otp_code.services import OTPCodeService
from api.user.serializers import ForgotPasswordSerializer, ResetPasswordWithTokenSerializer, VerifyOTPSerializer, ResetOTPPasswordSerializer

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
    permission_classes=[IsAuthenticated, IsProfileOwner]

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = {"detail": "Password updated successfully."}
        return response
    

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

class AvailableTechnicianListView(ListAPIView):
    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
    
            queryset = User.objects.filter(
                    role='technician'
            )
    
            return  queryset
    

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ResetPasswordThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        UserService.send_reset_email(serializer.user, request)

        return Response(
            {
                "detail": "Password reset email has been sent."
            },
            status=status.HTTP_200_OK
        )
    
class ResetPasswordWithTokenAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ResetPasswordThrottle]

    def post(self, request):
        serializer = ResetPasswordWithTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        UserService.reset_password(
            user=serializer.validated_data["user"],
            new_password=serializer.validated_data["password"],
            request=request
        )

        return Response(
            {
                "detail": "Password reset successful."
            },
            status=status.HTTP_200_OK,
        )

class ForgotPasswordOTPAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes=[ResetPasswordThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        if user:
            UserService.send_otp_reset_email(user=user,request=request)

        return Response({
            'message': 'If that email is associated with an account, '
               'a password reset code has been sent.'
        })


class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ResetPasswordThrottle]

    def post (self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        user = User.objects.filter(
            email=email,
            is_active=True
        ).first()

        if not user:
            raise ValidationError("Invalid or expired code.")

        reset_token = OTPCodeService.verify_code(
            user=user,
            code=code
            )

        return Response({
            "message": "Code verified successfully.",
            "reset_token": reset_token
        })

class OTPResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ResetPasswordThrottle]

    def post(self, request):
        serialializer = ResetOTPPasswordSerializer(data=request.data, context={'request': request})

        serialializer.is_valid(raise_exception=True)

        reset_token = serialializer.validated_data['reset_token']
        new_password = serialializer.validated_data['new_password']

        OTPCodeService.reset_password(
            reset_token=reset_token,
            new_password=new_password,
            request=request
        )

        return Response(
            {
                "message": "Password reset successfully."
            },
            status=status.HTTP_200_OK
        )