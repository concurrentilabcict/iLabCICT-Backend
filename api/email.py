import requests

from django.conf import settings
class EmailService:
    BASE_PASSWORD_RESET_URL = 'https://i-lab-cict-email-service.vercel.app/api/send-email'
    BASE_WELCOME_URL = 'https://i-lab-cict-email-service.vercel.app/api/send-welcome-email'

    @staticmethod
    def send_password_reset_email(
        *,
        recipient_email,
        recipient_name=None,
        reset_url
    ):

        headers = {
        "X-API-Key": settings.EMAIL_API_KEY,
        "Content-Type": "application/json",
        }

        payload = {
        "email": recipient_email,
        "name": recipient_name,
        "link": reset_url,
        }

        try:
            response = requests.post(EmailService.BASE_PASSWORD_RESET_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Failed to send reset email: {e}")
            return False

    @staticmethod
    def send_welcome_email(
        *,
        recipient_email,
        recipient_username=None,
        temp_password,
        recipient_fullname=None
    ):
        headers = {
            "X-API-Key": settings.EMAIL_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            'email': recipient_email,
            'username': recipient_username,
            'temp_password': temp_password,
            'name': recipient_fullname  
        }

        try:
            response = requests.post(EmailService.BASE_WELCOME_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Failed to send welcome email: {e}")
            return False



      