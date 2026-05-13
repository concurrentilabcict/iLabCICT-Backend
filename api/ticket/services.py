from api.ticket.models import Ticket

class TicketService:

    @staticmethod
    def get_all_by_status(status=None):
        queryset = Ticket.objects.all()

        if status:
            queryset = queryset.filter(status=status)

        return queryset
