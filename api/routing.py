from django.urls import path
from api.ticket.consumers import TicketConsumer
from api.notification.consumers import NotifcationConsumer

websocket_urlpatterns = [
    path('ws/tickets/', TicketConsumer.as_asgi()),
    path('ws/notifications/', NotifcationConsumer.as_asgi()),
]
