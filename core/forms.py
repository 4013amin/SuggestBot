from django import forms
from django.core.validators import RegexValidator

class OTPRequestForm(forms.Form):
    phone_number = forms.CharField(
        label="شماره موبایل",
        validators=[RegexValidator(r'^09\d{9}$', 'شماره موبایل معتبر نیست.')],
        widget=forms.TextInput(attrs={'placeholder': 'مثال: 09123456789'})
    )

class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        label="کد تایید",
        max_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'کد ۶ رقمی را وارد کنید'})
    )