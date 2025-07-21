import logging
import random
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from requests import Response
from rest_framework import permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from . import models
from . import notifications
from rest_framework.authtoken.models import Token
from . import serializers

logger = logging.getLogger(__name__)


# Create your views here.

class OTPRegister(APIView):
    permission_classes = [AllowAny]

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


class OTPLogin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = serializers.LoginOTP(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        user = get_object_or_404(models.User, username=phone_number)
        enter_code = get_object_or_404(models.OTPCode, user=user, code=code)
        if not enter_code.is_valid():
            return Response({"error": "کد وارد شده منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                token, _ = Token.objects.get_or_create(user=user)
                enter_code.delete()
                profile, created = models.ClientProfile.objects.get_or_create(user=user)
                if created:
                    profile.save()

        except Exception as e:
            logger.error(f"Error during OTP verification transaction for {user.username}: {e}", exc_info=True)
            return Response({"error": "خطای سیستمی در پردازش احراز هویت."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"token": token.key}, status=status.HTTP_200_OK)
