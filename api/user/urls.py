from django.urls import path
from api.user.views import UserListCreateView, UserDetailView

urlpatterns = [
    # GET all users, CREATE one user
    path('', UserListCreateView.as_view()),

    # GET, UPDATE, DELETE one user
    path('<int:pk>/', UserDetailView.as_view())
]
