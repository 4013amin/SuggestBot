from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dahsboard/', views.dashboard_overview_view, name='dashboard_overview'),
    path('', views.request_otp_view, name='request_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('connect-site/', views.connect_site_view, name='connect_site'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('product/<int:pk>/request-ai-recommendation/', views.request_ai_recommendation,
         name='request_ai_recommendation'),
    path('product/<int:pk>/abandonment/', views.product_abandonment_view, name='product_abandonment'),

    # تحلیل رقبا
    path('product/<int:pk>/competitor-comparison/', views.competitor_comparison_view, name='competitor_comparison'),

    path('product/<int:pk>/ai-chat/', views.ai_chat_recommendation, name='ai_chat_recommendation'),  # اضافه شده

    
    path('tracking-script.js', views.tracking_script_view, name='tracking_script'),
    path('api/track-event/', views.track_event_view, name='track_event'),
    
    path('product/<int:pk>/report-pdf/', views.product_report_pdf, name='product_report_pdf'),
    path('logout/', views.logout, name='logout'),
]
