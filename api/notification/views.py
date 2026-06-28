
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveUpdateAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService
from api.permissions import IsNotificationOwner
from rest_framework.permissions import IsAuthenticated

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NotificationService.get_all(
            user_id=self.request.user.id,
            type=self.request.query_params.get('type'),
            status=self.request.query_params.get('status'),
            date=self.request.query_params.get('date')
        )

class NotificationDetailView(RetrieveUpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated, IsNotificationOwner]
   
