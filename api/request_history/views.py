from rest_framework.generics import ListAPIView, RetrieveAPIView
from api.request_history.serializers import RequestHistorySerializer
from api.request_history.models import RequestHistory
from api.permissions import IsStaff
from rest_framework.permissions import IsAuthenticated
from api.request_history.services import RequestHistoryService
class RequestHistoryListView(ListAPIView):
    def get_queryset(self):
        return RequestHistoryService.get_all(room_id=self.request.query_params.get("room-id"))
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated, IsStaff]

class RequestHistoryDetailView(RetrieveAPIView):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated, IsStaff]

