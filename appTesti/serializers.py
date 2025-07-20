from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)

    def Is_valid(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError("فرمت شماره موبایل نامعتبر است.")
        return value


class LoginOTP(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)

    def Is_valid(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError("فرمت شماره موبایل نامعتبر است.")
        return value
