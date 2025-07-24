from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.request_otp_view, name='request_otp'),
    path('login/verify/', views.verify_otp_view, name='verify_otp'),
    path('dashboard/connect/', views.connect_site_view, name='connect_site'),
    # سایر URL های شما
]
