from django.urls import path
from api.user.views import UserListCreateView, UserDetailView, UserUpdatePassword, AvailableCustodianListView, ForgotPasswordAPIView

urlpatterns = [
    # GET all users, CREATE one user
    path('', UserListCreateView.as_view()),

    # GET, UPDATE, DELETE one user
    path('<int:pk>/', UserDetailView.as_view()),
    path('reset-password/<int:pk>/', UserUpdatePassword.as_view()),
    path('available-custodian/', AvailableCustodianListView.as_view()),
    path('forgot-password/send-email/', ForgotPasswordAPIView.as_view()),
]
