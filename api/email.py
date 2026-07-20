import requests

from django.conf import settings
class EmailService:
    BASE_URL = 'https://api.brevo.com/v3/smtp/email'

    @staticmethod
    def send_password_reset_email(
        *,
        recipient_email,
        recipient_name,
        reset_url
    ):
        
        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_KEY,
            "content-type": "application/json",
        }

        payload = {
            "sender": {
                "name": "iLabCICT",
                "email": settings.DEFAULT_FROM_EMAIL,
            },
            "to": [
                {
                    "email": recipient_email,
                    "name": recipient_name,
                }
            ],
            "subject": "Reset your password",
            "htmlContent": f"""
                <h2>Password Reset</h2>

                <p>Hello {recipient_name},</p>

                <p>
                    Someone requested to reset your password.
                </p>

                <p>
                    Click below:
                </p>

                <a href="{reset_url}">
                    Reset Password
                </a>

                <p>
                    This link expires in 15 minutes.
                </p>
            """,
        }

        response = requests.post(
            EmailService.BASE_URL,
            headers=headers,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()
        print(response.status_code)
        print(response.json())

        return response.json()