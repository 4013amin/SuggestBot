from rest_framework import serializers
from django.contrib.auth.models import User
from accounts.models import Store
from accounts.models import SubscriptionPlan, UserSubscription


# Profile users

class UserRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=11,
    )

    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError('Invalid phone number')
        return value


class UserVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError('Invalid code')
        return value


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'duration_days']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = ['plan', 'start_date', 'end_date', 'is_active']
