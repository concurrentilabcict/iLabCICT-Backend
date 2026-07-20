from api.user.models import User
from rest_framework.exceptions import ValidationError
from api.user.models import User
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
    
class UserService:

    @staticmethod
    @transaction.atomic
    def reset_password(user, new_password):
        user.set_password(new_password)
        user.save(update_fields=["password"])

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
        seven_days_ago = timezone.now() - timedelta(days=7)
        today = timezone.localdate()

        profile = User.objects.get(id=user.id)

        stats = {}

        if include and "faculty-stats" in include.split(",") and user.role == User.UserRole.FACULTY:
            tickets_per_day = (
                Ticket.objects
                .filter(
                    reported_by=user,
                    created_at__gte=seven_days_ago
                )
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )

            tickets_submitted_today = (
                Ticket.objects
                .filter(
                    reported_by=user,
                    created_at__gte=today
                )
                .values("type")
                .annotate(count=Count("id"))
            )

            stats["tickets_per_day"] = list(tickets_per_day)
            stats["total_tickets_last_7_days"] = (
                Ticket.objects.filter(
                    reported_by=user,
                    created_at__gte=seven_days_ago
                ).count()
            )
            stats["tickets_submitted_today"] = list(tickets_submitted_today)
            stats["total_tickets_today"] = (
                Ticket.objects.filter(
                    reported_by=user,
                    created_at__gte=today
                ).count()
            )

        return profile, stats
       
    @staticmethod
    def send_reset_email(user):
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
        except requests.HTTPError as e:
            print(e.response.text)
            raise

