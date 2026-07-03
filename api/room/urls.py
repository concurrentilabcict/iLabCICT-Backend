from django.urls import path
from api.room.views import RoomListCreateView, RoomDetailView, RoomAllComputersDetailView

urlpatterns = [
    # GET all rooms, CREATE one room with filters
    path('', RoomListCreateView.as_view()),

    # GET, UPDATE, DELETE one room
    path('<int:pk>/', RoomDetailView.as_view()),

    path('<int:pk>/computers/', RoomAllComputersDetailView.as_view())
]
