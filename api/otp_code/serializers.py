from rest_framework import serializers 
from api.otp_code.models import OTPCode

class OTPCodeSerializer(serializers):

    class Meta:
        model=OTPCode
        fields='__all__'