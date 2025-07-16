from django.urls import path

from . import views

urlpatterns = [
    path('OTP_register/', views.OTPRegisterView.as_view()),
    path('OTP_Verify/', views.OTPVerifyAPIView.as_view()),
    path('dashboard/', views.Dashboard.as_view())
]
