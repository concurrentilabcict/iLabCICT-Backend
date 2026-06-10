
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        pk = self.kwargs['pk']
        return NotificationService.get_all_notification_per_user(user_id=pk)

class NotificationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    http_method_names = ['patch', 'delete']
