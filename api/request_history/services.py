#services functions here.

from api.request_history.models import RequestHistory
class RequestHistoryService:

    @staticmethod
    def get_all(room_id=None):

        queryset = RequestHistory.objects.select_related('room',
                                                         'ticket',
                                                         'technician')

        if room_id is not None:
            queryset = queryset.filter(room_id=room_id)
        
        return queryset

   

