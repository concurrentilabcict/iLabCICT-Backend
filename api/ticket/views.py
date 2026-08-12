from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from api.ticket.models import Ticket
from api.ticket.serializers import TicketReadSerializer, TicketWriteSerializer
from api.ticket.services import TicketService
from api.permissions import IsAdmin, IsTechnician, IsFacultyReportedTicket, HasTicketPermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import urlencode
from django.conf import settings

class TicketListView(ListAPIView):
    serializer_class = TicketReadSerializer
    permission_classes = [IsAuthenticated, HasTicketPermission]

    def get(self, request, *args, **kwargs):
        cursor = request.query_params.get('cursor')
        query_search = request.query_params.get('q')
        type = request.query_params.get('type')
        status = request.query_params.get('status')
        date = request.query_params.get('date')

        try: 
            tickets, next_cursor = (
                TicketService.get_paginated_tickets(
                    user=request.user,
                    cursor=cursor,
                    query_search=query_search,
                    status=status,
                    type=type,
                    date=date
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
            
            if query_search:
                params['q'] = query_search

            if status:
                params['status'] = status

            if type:
                params['type'] = type

            if date:
                params['date'] = date

            next_url = (
                f'{settings.API_BASE_URL}'
                f'/api/tickets/paginated/'
                f'?{urlencode(params)}'
                )

        return Response({
            'results': TicketReadSerializer(
                tickets,
                many=True
            ).data,

            'next': next_url
        })


class TicketListCreateView(ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsFacultyReportedTicket()]
            
        return [IsAuthenticated(), HasTicketPermission()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketWriteSerializer
        
        return TicketReadSerializer
    
    def get_queryset(self):
        return TicketService.get_all(
            user=self.request.user,
            status=self.request.query_params.get('status'),
            technician_id=self.request.query_params.get('technician-id'),
            type=self.request.query_params.get('type'),
            date=self.request.query_params.get('date')
        )
    
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        ticket = TicketService.create_ticket(
            request=request,
            reported_by=request.user,
            validated_data=serializer.validated_data
        )

        return Response(
            TicketReadSerializer(ticket).data,
            status=status.HTTP_201_CREATED)

class TicketDetailView(RetrieveUpdateDestroyAPIView):

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), (IsAdmin | IsTechnician)()]
        elif self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdmin()]

        return [IsAuthenticated(), HasTicketPermission()]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        ticket = TicketService.update_ticket(
            request=request,
            instance=instance,
            validated_data=serializer.validated_data,
            technician=request.user
        )
        
        return Response(
            TicketReadSerializer(ticket).data
                        )
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return TicketWriteSerializer
        
        return TicketReadSerializer

    def get_queryset(self):
        return Ticket.objects.select_related(
            'reported_by',
            'assigned_to',
            'room',
            'computer'
        )
    
 
    def perform_destroy(self, instance):
        TicketService.delete_ticket(instance)

    http_method_names = ['patch', 'delete', 'get']

