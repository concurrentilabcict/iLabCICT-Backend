from django.urls import path
from api.computer.views import (
                                ComputerDetailView,
                                ComputerListCreateView, 
                                ActiveComputerListView,
                                ActiveComputerWithActivePeripheralsListView,
                                ActiveComputerWithPeripheralListView,
                                ActiveComputerNoPeripheralsView
                                )

urlpatterns = [
    path('', ComputerListCreateView.as_view()),

    path('<int:pk>/', ComputerDetailView.as_view()),

    path('active/', ActiveComputerListView.as_view()),
    path('active/peripherals/all/', ActiveComputerWithActivePeripheralsListView.as_view()),

    # with query params (type [eg. mouse, keyboard], status [eg. active, broken])
    path('active/peripherals/', ActiveComputerWithPeripheralListView.as_view()),

    path('active/peripherals/none/', ActiveComputerNoPeripheralsView.as_view())
]
