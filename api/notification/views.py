
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return NotificationService.get_all(
            user_id=self.request.query_params.get('user-id'),
            type=self.request.query_params.get('type'),
            status=self.request.query_params.get('status'),
            date=self.request.query_params.get('date')
        )

class NotificationDetailView(RetrieveAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
   
