from rest_framework.views import APIView
from api.user_push_token.serializers import UserPushTokenSerializer
from rest_framework.permissions import IsAuthenticated
from api.user_push_token.services import UserPushTokenService
from rest_framework.response import Response
from rest_framework import status
class UserPushTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        push_tokens = UserPushTokenService.get_push_tokens(user=request.user)

        serializer = UserPushTokenSerializer(
            push_tokens,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = UserPushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserPushTokenService.register_push_token(
            user=request.user,
            push_token=serializer.validated_data["push_token"]
        )

        return Response(
            {
                "detail": "Push token registered successfully."
            },
            status=status.HTTP_200_OK
        )

    
    