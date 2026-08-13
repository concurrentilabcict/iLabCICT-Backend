
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveUpdateAPIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService
from api.permissions import IsNotificationOwner
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from urllib.parse import urlencode

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')
        status = request.query_params.get('status')

        try:
            notifications, next_cursor = (
                NotificationService.get_paginated_notifications(
                    user=request.user,
                    cursor=cursor,
                    status=status
                )
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid cursor.'},
                status=400
            )

        next_url = None

        if next_cursor:
            params = {
                'cursor': next_cursor
            }

            if status:
                params['status'] = status

            next_url = (
                f'{settings.API_BASE_URL}'
                f'/api/notifications/user/'
                f'?{urlencode(params)}'
            )

        return Response({
            'results': NotificationSerializer(
                notifications, many=True
            ).data,

            'next': next_url
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
   
