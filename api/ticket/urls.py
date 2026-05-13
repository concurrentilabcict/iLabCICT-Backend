from django.urls import path
from api.ticket.views import TicketDetailView, TicketListCreateView, TicketStatusListView

urlpatterns = [
    path('', TicketListCreateView.as_view()),
    path('<int:pk>/', TicketDetailView.as_view()),

    path('status/', TicketStatusListView.as_view())
]
