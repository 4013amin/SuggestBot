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


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError("فرمت شماره موبایل نامعتبر است.")
        return value


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)


# Product
class ProductRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = ['name', 'price', 'source_id']


class UserEventSerializer(serializers.ModelSerializer):
    product_source_id = serializers.CharField(write_only=True)

    class Meta:
        model = models.UserEvent
        fields = ['session_id', 'event_type', 'product_source_id', 'extra_data']

    def create(self, validated_data):
        product_source_id = validated_data.pop('product_source_id')

        try:
            product = models.Product.objects.get(source_id=product_source_id)
        except models.Product.DoesNotExist:
            raise serializers.ValidationError({"product_source_id": "Product not found."})

        event = models.UserEvent.objects.create(product=product, **validated_data)
        return event



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = '__all__'