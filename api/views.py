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

from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer

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
    summary='Retrieve user profile',
    request=serializers.UserRegisterSerializer,
    responses={
        status.HTTP_200_OK: serializers.MessageSerializer,
    }
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
                trial_plan = SubscriptionPlan.objects.get(name='Trial - 1 Month Free')
                now = timezone.now()
                UserSubscription.objects.create(
                    user=user,
                    plan=trial_plan,
                    start_date=now,
                    end_date=now + timedelta(days=trial_plan.duration_days)
                )
            except SubscriptionPlan.DoesNotExist:
                logger.error("Trial subscription plan not found in the database!")

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
    summary="Verify OTP code and get authentication token",
    description="Verifies the OTP and if valid, returns the user's authentication token.",
    request=serializers.UserVerifySerializer,
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
class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = serializers.UserVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        try:
            otp_entry = OTPCode.objects.get(
                user__username=phone_number,
                code=code
            )
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

        except Exception as e:
            logger.error(f"Error during OTP verification for {user.username}: {e}", exc_info=True)
            return Response({"error": "خطای سیستمی در پردازش احراز هویت."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {
            'token': token.key,
        }
        return Response(response_data, status=status.HTTP_200_OK)



class SubscriptionPlanListView(generics.ListAPIView):
    queryset = SubscriptionPlan.objects.filter(is_public=True)
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionPlanSerializer

class MySubscriptionView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def get_object(self):

        return get_object_or_404(UserSubscription, user=self.request.user)