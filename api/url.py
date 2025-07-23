# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # View اصلی برای نمایش روت API
    api_root,

    # View های مربوط به احراز هویت
    OTPRegisterView,
    OTPVerifyView,

    # View های مربوط به اشتراک
    SubscriptionPlanListView,
    MySubscriptionView,
    BuySubscriptionView
    # ViewSet های مربوط به سایر بخش‌ها (که در آینده اضافه می‌شوند)
    # ProfileView,
    # StoreViewSet,
)

# یک روتر برای ViewSetها می‌سازیم. ViewSetها برای عملیات CRUD (ایجاد، خواندن، آپدیت، حذف) عالی هستند.
# چون Viewهای فعلی شما (مثل OTPRegisterView) از نوع APIView یا generics.ListAPIView هستند،
# آنها را به صورت دستی در urlpatterns اضافه می‌کنیم.
# router = DefaultRouter()
# router.register(r'stores', StoreViewSet, basename='store')


urlpatterns = [
    # یک آدرس روت که یک نمای کلی از API شما را نشان می‌دهد.
    # GET /api/v1/
    path('', api_root, name='api-root'),

    # --- بخش احراز هویت (Authentication) ---
    # این URL ها برای فرآیند ثبت‌نام و ورود با OTP استفاده می‌شوند.
    # POST /api/v1/auth/register/  (ارسال شماره تلفن برای دریافت کد)
    path('auth/register/', OTPRegisterView.as_view(), name='otp-register'),

    # POST /api/v1/auth/verify/    (ارسال کد و شماره تلفن برای دریافت توکن)
    path('auth/verify/', OTPVerifyView.as_view(), name='otp-verify'),

    # --- بخش اشتراک (Subscription) ---
    # این URL ها برای مدیریت و نمایش اطلاعات اشتراک کاربر استفاده می‌شوند.
    # GET /api/v1/subscriptions/plans/  (لیست طرح‌های قابل خرید)
    path('subscriptions/plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),

    # GET /api/v1/subscriptions/status/ (وضعیت اشتراک فعلی کاربر)
    path('subscriptions/status/', MySubscriptionView.as_view(), name='my-subscription-status'),

    #BY Plans
    path('subscription/buy/', BuySubscriptionView.as_view(), name='buy-subscription'),

    # --- سایر بخش‌ها (در آینده اضافه خواهند شد) ---
    # مثال برای URL های آینده:
    # path('profile/', ProfileView.as_view(), name='user-profile'),

    # اگر از ViewSet استفاده می‌کردید، این خط را اضافه می‌کردید:
    # path('', include(router.urls)),
]