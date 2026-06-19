
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        user = self.request.query_params.get("user-id")
        return NotificationService.get_all_notification_per_user(user_id=user)

class NotificationDetailView(RetrieveAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
   
