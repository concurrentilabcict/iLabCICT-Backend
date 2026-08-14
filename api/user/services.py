from api.user.models import User
from rest_framework.exceptions import ValidationError
from api.room.models import Room
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from api.ticket.models import Ticket
from rest_framework_simplejwt.tokens import AccessToken
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from api.email import EmailService
import requests
from api.audit_logs.services import AuditLogsService
from zoneinfo import ZoneInfo
class UserService:

    @staticmethod
    @transaction.atomic
    def reset_password(user, new_password, request):
        user.set_password(new_password)
        user.save(update_fields=["password"])

        AuditLogsService.log(
            request=request,
            performed_by=user,
            action_title='Successful password reset',
            action_summary=f"{user.get_full_name()} successfully updated it's user password.",
            metadata={
                'result': 'successful'
            }
        )

    @staticmethod
    def get_user_full_name(user_id):
        user = User.objects.filter(id=user_id).values('first_name','last_name').first()
        
        return f"{user['first_name']} {user['last_name']}"
    
    @staticmethod
    def get_all(is_active=None,
                role=None):
        
        UserService.validate_filter(is_active=is_active,
                                    role=role)
        
        queryset = User.objects.all()

        if is_active is not None:
        
            if is_active == 'true':
                is_active = True
            elif is_active == 'false':
                is_active = False

            queryset = queryset.filter(is_active=is_active)

        if role is not None:
            queryset = queryset.filter(role=role)

        return queryset
    
    @staticmethod
    def validate_filter(is_active,role):
        allowed_roles = User.UserRole.values

        if role and role not in allowed_roles:
            raise ValidationError('Invalid user role')
        
        if is_active not in ('true', 'false', None):
            raise ValidationError('is-active must only be True or False')


    @staticmethod
    def get_profile_stats(user, include=None):
        today = timezone.localdate()
        seven_days_ago = today - timedelta(days=6)

        profile = User.objects.get(id=user.id)

        weekday_map = {
            0: "M",
            1: "T",
            2: "W",
            3: "TH",
            4: "F",
            5: "SA",
            6: "SU",
                }

        if include and 'faculty-stats' in include.split(',') and user.role == User.UserRole.FACULTY:
            return UserService.get_faculty_stats(
                user=user,
                today=today,
                seven_days_ago=seven_days_ago,
                profile=profile,
                weekday_map=weekday_map
            )
        elif include and 'technician-stats' in include.split(',') and user.role == User.UserRole.TECHNICIAN:
            return UserService.get_technician_stats(
                user=user,
                today=today,
                seven_days_ago=seven_days_ago,
                profile=profile,
                weekday_map=weekday_map
            )

    @staticmethod
    def get_technician_stats(user, today, seven_days_ago, profile, weekday_map):
        stats = {}

        total_tickets_assigned_result = {
            'report_tickets': 0,
            'request_tickets': 0,
            'total': 0
        }

        total_tickets_assigned = (
            Ticket.objects
            .filter(
                assigned_to=user
            )
            .values('type')
            .annotate(count=Count('id'))
        )

        for ticket in total_tickets_assigned:
            if ticket['type'] == Ticket.TicketType.REQUEST:
                total_tickets_assigned_result['request_tickets'] = ticket['count']
                total_tickets_assigned_result['total'] += ticket['count']
            elif ticket['type'] == Ticket.TicketType.REPORT:
                total_tickets_assigned_result['report_tickets'] = ticket['count']
                total_tickets_assigned_result['total'] += ticket['count']

        total_tickets_assigned_today_result = {
            'report_tickets': 0,
            'request_tickets': 0,
            'total': 0
            }
        
        total_tickets_assigned_today = (
            Ticket.objects
            .filter(
                assigned_to=user,
                created_at__date=today
            )
            .values('type')
            .annotate(count=Count('id'))
        )

        for ticket in total_tickets_assigned_today:
            if ticket['type'] == Ticket.TicketType.REQUEST:
                total_tickets_assigned_today_result['request_tickets'] = ticket['count']
                total_tickets_assigned_today_result['total'] += ticket['count']
            elif ticket['type'] == Ticket.TicketType.REPORT:
                total_tickets_assigned_today_result['report_tickets'] = ticket['count']
                total_tickets_assigned_today_result['total'] += ticket['count']


        tickets_per_day_resolved = list(
            Ticket.objects
            .filter(
                assigned_to=user,
                status=Ticket.TicketStatus.RESOLVED,
                updated_at__gte=seven_days_ago
            )
            .annotate(day=TruncDate('updated_at', tzinfo=ZoneInfo('Asia/Manila')))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        last_seven_days = {}

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            last_seven_days[date] = {
                "day": weekday_map[date.weekday()],
                "count": 0,
                "date": date
            }

        for item in tickets_per_day_resolved:
            last_seven_days[item["day"]]["count"] = item["count"]


        assigned_tickets_per_status ={
            'open': 0,
            'ongoing': 0,
            'resolved': 0
        }


        assigned_tickets_status_today = (
            Ticket.objects
            .filter(
                assigned_to=user,
                created_at__date=today
                )
            .values('status')
            .annotate(count=Count("id"))
        )

        for ticket_status in assigned_tickets_status_today:
            if ticket_status['status'] == Ticket.TicketStatus.OPEN:
                assigned_tickets_per_status['open'] = ticket_status['count']
            elif ticket_status['status'] == Ticket.TicketStatus.ONGOING:
                assigned_tickets_per_status['ongoing'] = ticket_status['count']
            elif ticket_status['status'] == Ticket.TicketStatus.RESOLVED:
                assigned_tickets_per_status['resolved'] = ticket_status['count']

        stats['total_tickets_assigned'] = total_tickets_assigned_result
        stats['total_tickets_assigned_today'] = total_tickets_assigned_today_result
        stats['resolved_tickets_per_day'] = list(last_seven_days.values())
        stats['assigned_ticket_status_today'] = assigned_tickets_per_status
        return profile, stats


    @staticmethod
    def get_faculty_stats(user, today, seven_days_ago, profile,weekday_map):
        stats={}
        tickets_submitted_today = (
                        Ticket.objects
                        .filter(
                            reported_by=user,
                            created_at__date=today
                        )
                        .values("type")
                        .annotate(count=Count("id"))
                    )

        tickets_submitted = {
            "request_tickets": 0,
            "report_tickets": 0, 
        }

        for ticket in tickets_submitted_today:
            if ticket["type"] == Ticket.TicketType.REQUEST:
                tickets_submitted["request_tickets"] = ticket["count"]
            if ticket["type"] == Ticket.TicketType.REPORT:
                tickets_submitted["report_tickets"] = ticket["count"]

        tickets_per_day = list(
            Ticket.objects
            .filter(
                reported_by=user,
                created_at__date__gte=seven_days_ago
            )
            .annotate(day=TruncDate("created_at", tzinfo=ZoneInfo('Asia/Manila')))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        last_seven_days = {}

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            last_seven_days[date] = {
                "day": weekday_map[date.weekday()],
                "count": 0,
                "date": date
            }

        for item in tickets_per_day:
            last_seven_days[item["day"]]["count"] = item["count"]

        stats["tickets_per_day"] = list(last_seven_days.values())

        stats["tickets_submitted_today"] = tickets_submitted

        stats["total_tickets_today"] = (
            Ticket.objects.filter(
                reported_by=user,
                created_at__date=today
            ).count()
        )

        return profile, stats

    @staticmethod
    def send_welcome_email(user, temp_password=None):
        if temp_password is None:
            return

        try:
            EmailService.send_welcome_email(
                recipient_email=user.email,
                recipient_username=user.username,
                recipient_fullname=user.first_name,
                temp_password=temp_password
            )

        except requests.HTTPError as e:
            raise
       
    @staticmethod
    def send_reset_email(user, request):
        token = AccessToken()

        token["user_id"] = user.id
        token["purpose"] = "password_reset"

        token.set_exp(lifetime=timedelta(minutes=15))

        magic_link = (
           "https://i-lab-cict-web.vercel.app"
            f"/reset-password?token={token}"
        )

        try:
            EmailService.send_password_reset_email(
                recipient_email=user.email,
                recipient_name=user.first_name,
                reset_url=magic_link,
            )

            AuditLogsService.log(
                request=request,
                action_title='Password reset requested',
                action_summary=f'{user.get_full_name()} requested a password reset.',
                metadata={
                    'result': 'successful',
                }
            )

        except requests.HTTPError as e:
            AuditLogsService.log(
                request=request,
                performed_by=user,
                action_title="Password reset request failed",
                action_summary=f"Failed to send password reset email to {user.get_full_name()}.",
                metadata={
                    "result": "failed",
                    "error": str(e),
                }
            )
            raise

