from django.urls import path
from api.room.views import RoomListCreateView, RoomDetailView, RoomAllComputersDetailView,RoomWithComputerCodeDetailView, RoomNameWithComputerCodeDetailView,RoomNameAllComputersDetailView

urlpatterns = [
    # GET all rooms, CREATE one room with filters
    path('', RoomListCreateView.as_view()),

    # GET, UPDATE, DELETE one room
    path('<int:pk>/', RoomDetailView.as_view()),

    path('<int:pk>/computers/', RoomAllComputersDetailView.as_view()),
    path('<int:pk>/computers/<str:uk>/', RoomWithComputerCodeDetailView.as_view()),

    path('<str:room>/computers/', RoomNameAllComputersDetailView.as_view()),
    path('<str:room>/computers/<str:uk>/', RoomNameWithComputerCodeDetailView.as_view())
]
