from http.client import responses
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status, request, generics
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from accounts.models import User, Store, OTPCode, SubscriptionPlan, UserSubscription
from . import serializers
import logging
from rest_framework.views import APIView
import random
from rest_framework.authtoken.models import Token
from datetime import timedelta
from django.utils import timezone

from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer, BuySubscriptionSerializer

logger = logging.getLogger(__name__)


# Create your views here.
@extend_schema(exclude=True)
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'auth': 'Access /api/auth/ for authentication.',
        'profile': 'Access /api/profile/ to view/edit your profile.',
        'sites': 'Access /api/sites/ to manage WordPress sites.',
        'ai_generation': 'Access /api/ai/ for article generation.',
        'articles': 'Access /api/articles/ for article history.',
        'subscription': 'Access /api/subscription/ for plans and payments.',
        'tickets': 'Access /api/tickets/ for support tickets.',
        'docs': 'Access /api/schema/swagger-ui/ for full API documentation.',
    })


# RegisterUsers
@extend_schema(
    summary='ثبت نام یا ایجاد کاربر جدید با شماره تلفن',
    description="""
    این endpoint برای ثبت نام یا ورود اولیه کاربر با شماره تلفن استفاده می‌شود.
    مراحل کار:
    - دریافت شماره تلفن از کاربر.
    - ایجاد کاربر جدید در صورت عدم وجود.
    - اختصاص خودکار پلن آزمایشی رایگان (یک ماهه) به کاربران جدید.
    - تولید و ذخیره کد OTP شش رقمی.
    - ارسال (در اینجا فقط چاپ در کنسول) کد OTP برای تایید شماره تلفن.
    """,
    request=serializers.UserRegisterSerializer,
    responses={status.HTTP_200_OK: serializers.MessageSerializer}
)
class OTPRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = serializers.UserRegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']

        user, created = User.objects.get_or_create(username=phone_number)

        if created:
            user.set_unusable_password()
            user.save()

            try:
                trial_plan = SubscriptionPlan.objects.get(is_trial=True)
                if not UserSubscription.objects.filter(user=user, plan__is_trial=True).exists():
                    now = timezone.now()
                    UserSubscription.objects.create(
                        user=user,
                        plan=trial_plan,
                        start_date=now,
                        end_date=now + timedelta(days=trial_plan.duration_days)
                    )
            except SubscriptionPlan.DoesNotExist:
                logger.error("پلن آزمایشی (trial plan) در سیستم تعریف نشده است!")

        code = str(random.randint(100000, 999999))
        OTPCode.objects.filter(user=user).delete()
        OTPCode.objects.create(user=user, code=code)

        # SMS_SENDER method
        print(f"OTP for {phone_number} is: {code}")

        return Response(
            {"message": "کد تایید با موفقیت ارسال شد."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    summary="تایید کد OTP و دریافت توکن احراز هویت",
    description="""
    این endpoint کد OTP ارسال شده را بررسی می‌کند.
    - اگر کد و شماره تلفن معتبر باشند و کد منقضی نشده باشد:
        - توکن احراز هویت برای کاربر تولید یا بازیابی می‌شود.
        - کد OTP مصرف و حذف می‌گردد.
        - توکن به عنوان پاسخ بازگردانده می‌شود.
    - در غیر این صورت، خطای مناسب بازگردانده می‌شود.
    """,
    request=serializers.UserVerifySerializer,
    responses={
        200: serializers.AuthTokenSerializer,
        400: {"description": "ورودی نامعتبر، کد منقضی شده یا کاربر یافت نشد"},
        500: {"description": "خطای داخلی سرور"},
    },
    examples=[
        OpenApiExample(
            'موفقیت ورود',
            summary='تایید موفق کد و بازگردانی توکن',
            value={'token': '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'},
            response_only=True,
            status_codes=['200']
        ),
    ]
)
class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = serializers.UserVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        try:
            otp_entry = OTPCode.objects.get(user__username=phone_number, code=code)
        except OTPCode.DoesNotExist:
            return Response({'error': 'کد وارد شده یا شماره تلفن نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_entry.is_valid():
            return Response({'error': 'کد تایید منقضی شده است. لطفاً دوباره درخواست دهید.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = otp_entry.user

        try:
            with transaction.atomic():
                token, _ = Token.objects.get_or_create(user=user)
                otp_entry.delete()

                response_data = {'token': token.key}
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error during OTP verification for {user.username}: {e}", exc_info=True)
            return Response({"error": "خطای سیستمی در پردازش احراز هویت."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="لیست پلن‌های اشتراک عمومی",
    description="این endpoint لیست تمام پلن‌های اشتراکی را که به صورت عمومی در دسترس هستند بازمی‌گرداند.",
    responses={200: SubscriptionPlanSerializer(many=True)}
)
class SubscriptionPlanListView(generics.ListAPIView):
    queryset = SubscriptionPlan.objects.filter(is_public=True)
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionPlanSerializer


@extend_schema(
    summary="نمایش اشتراک فعال کاربر",
    description="این endpoint اطلاعات اشتراک فعلی کاربر را نمایش می‌دهد.",
    responses={200: UserSubscriptionSerializer}
)
class MySubscriptionView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def get_object(self):
        return get_object_or_404(UserSubscription, user=self.request.user)


@extend_schema(
    summary="خرید یا تمدید پلن اشتراک",
    description="""
    این endpoint برای خرید یا تمدید پلن اشتراک استفاده می‌شود.
    - کاربر فقط باید آیدی پلن (`plan_id`) را ارسال کند.
    - سرور بررسی می‌کند که پلن وجود دارد و عمومی است.
    - اگر کاربر قبلاً اشتراک داشته باشد، تمدید می‌شود.
    - اگر نداشته باشد، اشتراک جدید ایجاد می‌شود.
    - پاسخ شامل پیام موفقیت، تاریخ شروع و پایان و نام پلن است.
    """,
    request=BuySubscriptionSerializer,
    responses={
        200: {
            'message': 'پلن ... با موفقیت برای شما فعال شد.',
            'start_date': 'تاریخ شروع اشتراک',
            'end_date': 'تاریخ پایان اشتراک',
            'plan': 'نام پلن خریداری شده'
        },
        400: {'error': 'آیدی پلن ارسال نشده است.'},
        404: {'error': 'چنین پلنی وجود ندارد.'}
    }
)
class BuySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = BuySubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        plan_id = serializer.validated_data['plan_id']

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_public=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'چنین پلنی وجود ندارد یا قابل خرید نیست.'}, status=404)

        if plan.is_trial:
            return Response({'error': 'پلن آزمایشی قابل خریداری نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'start_date': now,
                'end_date': now + timedelta(days=plan.duration_days)
            }
        )

        return Response({
            'message': f'پلن {plan.name} با موفقیت برای شما فعال شد.',
            'start_date': subscription.start_date,
            'end_date': subscription.end_date,
            'plan': plan.name
        })
