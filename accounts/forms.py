from django import forms


class OTPRequestForm(forms.Form):
    phone_number = forms.EmailField(label="شماره تماس", widget=forms.EmailInput(attrs={'placeholder': 'شماره خود را وارد کنید'}))


class OTPVerifyForm(forms.Form):
    code = forms.CharField(label="کد تایید", max_length=6, widget=forms.TextInput(attrs={'placeholder': 'کد ۶ رقمی'}))
