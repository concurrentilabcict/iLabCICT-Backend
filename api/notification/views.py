
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveUpdateAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService
from api.permissions import IsNotificationOwner
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')

        try:
            notifications, next_cursor = (
                NotificationService.get_paginated_notifications(
                    user=request.user,
                    cursor=cursor
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        return Response({
            'results': NotificationSerializer(
                notifications, many=True
            ).data,

            'next': (
                f'{settings.API_BASE_URL}'
                f'/api/notifications/user'
                f'?cursor={next_cursor}'
                if next_cursor
                else None
            )
        })

    def get_queryset(self):
        return NotificationService.get_all(
            user=self.request.user,
            type=self.request.query_params.get('type'),
            status=self.request.query_params.get('status'),
            date=self.request.query_params.get('date')
        )

class NotificationDetailView(RetrieveUpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated, IsNotificationOwner]
   
