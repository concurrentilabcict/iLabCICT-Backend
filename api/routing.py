from django.urls import path
from api.ticket.consumers import TicketConsumer

websocket_urlpatterns = [
    path('ws/tickets/', TicketConsumer.as_asgi()),
]
