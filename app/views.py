from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from . import models
from . import serializers
import logging
import random
from . import notifications
from drf_spectacular.utils import extend_schema, OpenApiExample
logger = logging.getLogger(__name__)


# Create your views here.

@extend_schema(
    summary="۱. درخواست کد تایید (OTP)",  # خلاصه کوتاه
    description="""
این اندپوینت یک شماره موبایل از کاربر دریافت می‌کند و یک کد تایید ۶ رقمی برای او ارسال می‌کند.

**فرآیند کار:**
1. شماره موبایل کاربر را در بدنه درخواست دریافت می‌کند.
2. اگر کاربری با این شماره وجود نداشته باشد، یک کاربر جدید می‌سازد.
3. یک کد OTP تولید کرده و آن را از طریق SMS ارسال می‌کند.

- در صورت موفقیت، کاربر باید به صفحه **"تایید کد"** هدایت شود.
- این اولین مرحله از فرآیند ورود/ثبت‌نام است.
        """,
    request=serializers.OTPRegisterSerializer,  # مشخص کردن سریالایزر درخواست
    responses={
        400: serializers.OTPRegisterSerializer,  # حالا این خط صحیح است
    },
    examples=[
        OpenApiExample(
            'مثال درخواست صحیح',
            summary='یک نمونه درخواست معتبر',
            description='این یک مثال برای ارسال یک شماره موبایل صحیح است.',
            value={
                "phone_number": "09123456789"
            },
            request_only=True,
        ),
        OpenApiExample(
            'پاسخ موفقیت‌آمیز',
            summary='پاسخ سرور در صورت ارسال موفق SMS',
            value={
                "message": "OTP code sent successfully."
            },
            response_only=True,
            status_codes=['200']
        ),
        OpenApiExample(
            'پاسخ خطای سرور',
            summary='پاسخ سرور در صورت مشکل در ارسال SMS',
            value={
                "error": "Failed to send OTP code. Please try again later."
            },
            response_only=True,
            status_codes=['500']
        ),
    ]
)
class OTPRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = serializers.OTPRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']

        user, user_created = models.User.objects.get_or_create(username=phone_number)

        if user_created:
            user.set_unusable_password()
            user.save()
            models.Profile.objects.create(user=user, phone=phone_number)

        code = str(random.randint(100000, 999999))

        models.OTPCode.objects.filter(user=user).delete()

        models.OTPCode.objects.create(user=user, code=code)

        sms_sent_successfully = notifications.send_sms(phone_number, f"کد تایید شما: {code}")

        if sms_sent_successfully:
            return Response({"message": "OTP code sent successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Failed to send OTP code. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="Verify OTP code and get authentication token",
    description="Verifies the OTP and if valid, returns the user's authentication token.",
    request=serializers.OTPVerifySerializer,
    responses={
        200: serializers.AuthTokenSerializer,
        400: {"description": "Invalid input, code expired, or user not found"},
        500: {"description": "Internal server error"},
    },
    examples=[
        OpenApiExample(
            'Login Success',
            summary='Successful verification returns a token',
            value={'token': '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'},
            response_only=True,
            status_codes=['200']
        ),
    ]
)
class OTPVerifyAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = serializers.OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        user = get_object_or_404(models.User, username=phone_number)
        code_enter = get_object_or_404(models.OTPCode, user=user, code=code)

        if not code_enter.is_valid():
            return Response({"error": "کد وارد شده منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                token, _ = Token.objects.get_or_create(user=user)
                code_enter.delete()
                profile, created = models.Profile.objects.get_or_create(user=user)
                is_new_user = profile.is_new_user
                if created:
                    profile.is_new_user = is_new_user
                    profile.save()
        except Exception as e:
            logger.error(f"Error during OTP verification transaction for {user.username}: {e}", exc_info=True)
            return Response({"error": "خطای سیستمی در پردازش احراز هویت."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"token": token.key}, status=status.HTTP_200_OK)
