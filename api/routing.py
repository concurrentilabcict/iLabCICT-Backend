from django.urls import path
from api.ticket.consumers import TicketConsumer
from api.notification.consumers import NotifcationConsumer
from api.room.consumers import RoomConsumer
from api.report.consumers import ReportConsumer

websocket_urlpatterns = [
    path('ws/tickets/', TicketConsumer.as_asgi()),
    path('ws/notifications/', NotifcationConsumer.as_asgi()),
    path('ws/rooms/', RoomConsumer.as_asgi()),
    path('ws/reports', ReportConsumer.as_asgi()),
]
