import random

from django.contrib.auth.models import User
from django.shortcuts import render
from requests import Response
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from . import models
from . import notifications

from . import serializers


# Create your views here.

class OTPRegister(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']

        user, user_created = User.objects.get_or_create(username=phone_number)
        if user_created:
            user.set_unusable_password()
            user.save()
            models.ClientProfile.objects.create(user=user)

        code = random.randint(100000, 999999)

        models.OTPCode.objects.filter(code=code).delete()
        models.OTPCode.objects.create(user=user, code=code)
        send_sms = notifications.send_sms_Testi(phone_number, f"your Code is {code}")
        if send_sms:
            return Response(send_sms, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Failed to send OTP code. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

