from rest_framework.generics import ListAPIView, RetrieveAPIView
from api.request_history.serializers import RequestHistorySerializer
from api.request_history.models import RequestHistory
from api.permissions import IsStaff
from rest_framework.permissions import IsAuthenticated
class RequestHistoryListView(ListAPIView):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated, IsStaff]

class RequestHistoryDetailView(RetrieveAPIView):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated, IsStaff]

