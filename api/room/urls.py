from django.urls import path
from api.room.views import RoomListCreateView, RoomDetailView, RoomStatusListView, RoomPerBuildingListView, RoomPerNameListView

urlpatterns = [
    # GET all rooms, CREATE one room
    path('', RoomListCreateView.as_view()),

    # GET, UPDATE, DELETE one room
    path('<int:pk>/', RoomDetailView.as_view()),

    #filter
    path('status/', RoomStatusListView.as_view()),

    path('building/', RoomPerBuildingListView.as_view()),

    path('room/', RoomPerNameListView.as_view())
]
