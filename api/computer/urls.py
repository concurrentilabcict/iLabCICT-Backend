from django.urls import path
from api.computer.views import (
                                ComputerDetailView,
                                ComputerListCreateView, 
                                ActiveComputerListView,
                                ActiveComputerWithActivePeripheralsListView,
                                ActiveComputerWithPeripheralListView,
                                ActiveComputerNoPeripheralsView,
                                ComputerCodeDetailView,
                                ArchiveComputerView,
                                UnarchiveComputerView,
                                AllArchivedComputerView
                                )

urlpatterns = [
    path('', ComputerListCreateView.as_view()),
    path('archive/', AllArchivedComputerView.as_view()),

    path('<int:pk>/', ComputerDetailView.as_view()),

    path('<str:uk>/', ComputerCodeDetailView.as_view()),

    path('<int:pk>/archive/', ArchiveComputerView.as_view()),
    path('<int:pk>/unarchive/', UnarchiveComputerView.as_view()),

    path('active/', ActiveComputerListView.as_view()),
    path('active/peripherals/all/', ActiveComputerWithActivePeripheralsListView.as_view()),

    # with query params (type [eg. mouse, keyboard], status [eg. active, broken])
    path('active/peripherals/', ActiveComputerWithPeripheralListView.as_view()),

    path('active/peripherals/none/', ActiveComputerNoPeripheralsView.as_view())
]
