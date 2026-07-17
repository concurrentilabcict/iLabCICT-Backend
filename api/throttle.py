from rest_framework.throttling import AnonRateThrottle

class LoginThrottle(AnonRateThrottle):
    rate= "5/minute"