from django.shortcuts import render
from rest_framework.views import APIView
import random
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import OTPRequestForm, OTPVerifyForm
from .models import User, OTPCode, ApiKey
# Create your views here.



def request_otp_view(request):
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            # اگر کاربر وجود نداشت، او را می‌سازیم
            user, created = User.objects.get_or_create(username=phone_number, defaults={'username': phone_number})

            # تولید کد OTP
            code = str(random.randint(100000, 999999))
            OTPCode.objects.create(user=user, code=code)

            # --- ارسال کد به کاربر ---
            # در یک پروژه واقعی، اینجا کد را با ایمیل یا SMS ارسال می‌کنید.
            # برای تست، ما آن را در کنسول چاپ می‌کنیم.
            print(f"کد تایید برای {phone_number} : {code}")
            # -------------------------

            # ایمیل کاربر را در سشن ذخیره می‌کنیم تا در مرحله بعد از آن استفاده کنیم
            request.session['otp_user_email'] = phone_number
            return redirect('accounts:verify_otp')
    else:
        form = OTPRequestForm()
    return render(request, 'accounts/request_otp.html', {'form': form})


def verify_otp_view(request):
    user_email = request.session.get('otp_user_email')
    if not user_email:
        return redirect('accounts:request_otp')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                user = User.objects.get(email=user_email)
                otp = OTPCode.objects.get(user=user, code=code)

                if otp.is_valid():
                    login(request, user)
                    otp.delete()  # کد استفاده شده را حذف می‌کنیم
                    del request.session['otp_user_email']
                    return redirect('accounts:connect_site')  # ریدایرکت به صفحه اصلی داشبورد
                else:
                    form.add_error('code', 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')

            except (OTPCode.DoesNotExist, User.DoesNotExist):
                form.add_error('code', 'کد وارد شده صحیح نیست.')
    else:
        form = OTPVerifyForm()
    return render(request, 'accounts/verify_otp.html', {'form': form})


@login_required
def connect_site_view(request):
    api_key_obj = ApiKey.objects.get(user=request.user)
    context = {
        'api_key': api_key_obj
    }
    return render(request, 'app/app/connect_site.html', context)
