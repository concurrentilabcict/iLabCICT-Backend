import base64
import json
from django.utils.dateparse import parse_datetime

class TicketCursorService:

    @staticmethod
    def encode_cursor(ticket):
        payload = {
            'status_priority': ticket.status_priority,
            'created_at': ticket.created_at.isoformat(),
            'id': ticket.id,
        }

        encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode()

        return encoded

    @staticmethod
    def decode_cursor(cursor):
        try:
            decoded = base64.urlsafe_b64decode(
                cursor.encode()
            ).decode()

            data = json.loads(decoded)

            created_at = parse_datetime(
                data['created_at']
            )

            if created_at is None:
                return None

            return {
                'status_priority': int(
                    data['status_priority']
                ),
                'created_at': created_at,
                'id': int(data['id']),
            }


        except (
            ValueError,
            TypeError,
            json.JSONDecodeError,
            KeyError,
            UnicodeDecodeError
            ):
            return None

        
class CursorService:
    @staticmethod
    def encode_cursor(obj):
        payload = {
            'id': obj.id,
            'created_at': obj.created_at.isoformat(),
        }

        encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode()

        return encoded

    @staticmethod
    def decode_cursor(cursor):
        try:
            decoded = base64.urlsafe_b64decode(
                cursor.encode()
            ).decode()

            return json.loads(decoded)

        except (ValueError, TypeError, json.JSONDecodeError):
            return None 

class SingleCursorService:
    @staticmethod
    def encode_cursor(obj):
        payload = {
            'id': obj.id,
        }

        encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode()

        return encoded

    @staticmethod
    def decode_cursor(cursor):
        try:
            decoded = base64.urlsafe_b64decode(
                cursor.encode()
            ).decode()

            return json.loads(decoded)

        except (ValueError, TypeError, json.JSONDecodeError):
            return None 