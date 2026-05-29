from django.urls import path
from api.chatbot.views import ChatView, ChatResetView

urlpatterns = [
    path('', ChatView.as_view()),
    path('reset/', ChatResetView.as_view())
]