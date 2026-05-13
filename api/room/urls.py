from django.urls import path
from api.room.views import RoomListCreateView, RoomDetailView, RoomStatusListView

urlpatterns = [
    # GET all rooms, CREATE one room
    path('', RoomListCreateView.as_view()),

    # GET, UPDATE, DELETE one room
    path('<int:pk>/', RoomDetailView.as_view()),

    path('status/', RoomStatusListView.as_view())
]
