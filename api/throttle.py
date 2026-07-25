from rest_framework.throttling import AnonRateThrottle

class LoginThrottle(AnonRateThrottle):
    rate= "5/minute"

class ResetPasswordThrottle(AnonRateThrottle):
    rate= "3/minute"