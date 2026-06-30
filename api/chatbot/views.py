
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.chatbot.services import ChatbotService
from api.permissions import IsTechnician
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

class ChatView(APIView):

    permission_classes = [IsAuthenticated, IsTechnician]
    def post(self, request):

        user_message = request.data.get('message','').strip()

        if not user_message:
            raise ValidationError('Message cannot be empty')
        
        result = ChatbotService.process_conversation(request.session, user_message)
        return Response(result, status=status.HTTP_200_OK)
    
class ChatResetView(APIView):

    permission_classes = [IsAuthenticated, IsTechnician]
    def post(self, request):
        request.session.flush()
        return Response(
            {'detail': 'Chat session reset.'},
            status=status.HTTP_200_OK
        )
