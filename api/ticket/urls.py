from django.urls import path
from api.ticket.views import TicketDetailView, TicketListCreateView, TicketListView,ArchiveAdminTicketView

urlpatterns = [
    path('', TicketListCreateView.as_view()),
    path('<int:pk>/', TicketDetailView.as_view()),
    path('paginated/', TicketListView.as_view()),
    path('<int:pk>/archive/', ArchiveAdminTicketView.as_view()),


]
