import secrets

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import process_pending_events, replication_status


class Operator:
    is_authenticated = True


class ReplicationAuthentication(BaseAuthentication):
    """Dedicated 256-bit bearer secret over HTTPS; independent of business JWTs.

    QStash forwards this through Upstash-Forward-Authorization. No body can
    specify tables, SQL, aliases, limits, or a change to the server configuration.
    """
    def authenticate(self, request):
        secret = getattr(settings, "REPLICATION_TOKEN", "")
        supplied = request.headers.get("Authorization", "")
        if len(secret) < 43 or not secrets.compare_digest(supplied.encode(), ("Bearer " + secret).encode()):
            raise AuthenticationFailed("Invalid replication credentials.")
        return Operator(), None

    def authenticate_header(self, request):
        return "Bearer"


class ReplicationView(APIView):
    authentication_classes = [ReplicationAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class ProcessView(ReplicationView):
    def post(self, request):
        if request.query_params or request.body.strip() not in (b"", b"{}"):
            return Response({"error": "Request parameters are not supported."}, status=400)
        try:
            result = process_pending_events()
        except Exception:
            return Response({"outcome": "UNAVAILABLE"}, status=503)
        status = 503 if result["outcome"] in {"UNAVAILABLE", "RETRY"} else 409 if result["outcome"] == "BLOCKED" else 200
        return Response(result, status=status)


class StatusView(ReplicationView):
    def get(self, request):
        return Response(replication_status())
