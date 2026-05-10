from django.urls import path
from api.computer.views import ComputerDetail, ComputerListCreateView

urlpatterns = [
    path('', ComputerListCreateView.as_view()),

    path('<int:pk>/', ComputerDetail.as_view())
]
