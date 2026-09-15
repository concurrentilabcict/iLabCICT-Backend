import secrets
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from api.otp_code.models import OTPCode
from datetime import  timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo
from api.audit_logs.services import AuditLogsService
class OTPCodeService:

    ph_tz = ZoneInfo('Asia/Manila')

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def generate_reset_token():
        token_id = secrets.token_hex(16)
        secret = secrets.token_urlsafe(32)

        reset_token = f"{token_id}.{secret}"

        return token_id, secret, reset_token


    @staticmethod
    def verify_code(user, code):

        reset = OTPCode.objects.filter(
            user=user,
            used_at__isnull=True,
            verified_at__isnull=True,
        ).order_by('-created_at').first()

        if not reset:
            raise ValidationError("Invalid or expired code.")

        now = timezone.now()

        if now >= reset.expires_at:
            raise ValidationError("Code has expired.")

        if not check_password(code, reset.code_hash):
            reset.attempts += 1
            reset.save(update_fields=['attempts'])

            raise ValidationError("Invalid code.")

        token_id, secret, reset_token = (
            OTPCodeService.generate_reset_token()
        )

        reset.verified_at = now
        reset.token_id = token_id
        reset.reset_token_hash = make_password(secret)
        reset.attempts += 1
        reset.reset_token_expires_at = (now + timedelta(minutes=10))

        reset.save(
            update_fields=[
                'verified_at',
                'token_id',
                'reset_token_hash',
                'reset_token_expires_at',
                'attempts',
            ]
        )

        return reset_token

    @staticmethod
    def reset_password(reset_token, new_password, request):
        try:
            token_id, secret = reset_token.split('.', 1)
        except ValueError:
            raise ValidationError("Invalid Reset Token.")

        reset = OTPCode.objects.filter(
            token_id=token_id,
            verified_at__isnull=False,
            used_at__isnull=True
        ).first()

        if not reset:
            raise ValidationError("Invalid reset token.")

        now = timezone.now()

        if (
            reset.reset_token_expires_at is None
            or now >= reset.reset_token_expires_at
        ):
            raise ValidationError("Reset token has expired.")

        if not check_password(secret, reset.reset_token_hash):
            raise ValidationError("Invalid reset token.")

        user = reset.user

        user.set_password(new_password)

        user.save(update_fields=['password'])

        reset.used_at = now

        reset.save(
            update_fields=['used_at']
        )

        AuditLogsService.log(
            request=request,
            performed_by=user,
            action_title='Succesful password reset',
            action_summary=f'{user.get_full_name()} successfully changed their account password.',
            metadata={
                'status': 'successful'
            }
        )

        return user

    @staticmethod
    def create_reset_code(user):


        OTPCode.objects.filter(
            user=user,
            used_at__isnull=True,
            verified_at__isnull=True
        ).update(
            used_at=timezone.now()
        )

        code = OTPCodeService.generate_code()

        reset = OTPCode.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=15)
        )

        time = timezone.localtime(timezone.now() + timedelta(minutes=15), OTPCodeService.ph_tz)
        time = time.strftime("%I:%M %p")

        return reset, code, time


    
    
