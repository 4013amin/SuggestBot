from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # مسیرهای ورود
    path('', views.request_otp_view, name='request_otp'),
    path('login/verify/', views.verify_otp_view, name='verify_otp'),

    # مسیرهای داشبورد و تحلیل
    path('connect/', views.connect_site_view, name='connect_site'),
    path('dashboard/', views.dashboard_overview_view, name='dashboard_overview'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('logout/', views.logout, name='logout'),
]
