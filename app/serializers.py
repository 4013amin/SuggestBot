from rest_framework import serializers
from django.contrib.auth.models import User
from . import models


class OTPRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must be numeric.")
        if len(value) != 11:
            raise serializers.ValidationError("Phone number must be 11 digits long.")
        if not value.startswith('09'):
            raise serializers.ValidationError("Phone number must start with '09'.")
        return value
