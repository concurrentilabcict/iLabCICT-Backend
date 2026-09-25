
from rest_framework.generics import ListAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.views import APIView
from api.notification.models import Notification
from api.notification.serializers import NotificationSerializer
from api.notification.services import NotificationService
from api.permissions import IsNotificationOwner
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from urllib.parse import urlencode

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')

        try:
            notifications, next_cursor = (
                NotificationService.get_paginated_notifications(
                    user=request.user,
                    cursor=cursor,
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

            next_url = (
                f'{settings.API_BASE_URL}'
                f'/api/notifications/user/'
                f'?{urlencode(params)}'
            )

        return Response({
            'results': NotificationSerializer(
                notifications, many=True,context={"user": request.user}
            ).data,

            'next': next_url
        })

class NotificationDetailView(RetrieveUpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def get_queryset(self):
        return Notification.objects.exclude(
            archived_by__contains=[self.request.user.id]
        )

class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def post(self, request, pk):
        try:
            NotificationService.mark_as_read(
                user=request.user,
                pk=pk
            )
            return Response(
                {"detail": "Notification marked as read."},
                status=status.HTTP_200_OK
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class NotificationArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def post(self, request, pk):
        try:
            NotificationService.archive_notification(user=request.user, pk=pk)
            return Response(
                    {"detail": "Notification archived succesfully."},
                    status=status.HTTP_200_OK
                )
        except:
            return Response(
                    {"detail": "Notification not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            



        
        


   
