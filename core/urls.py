from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Auth
    path('login/', views.request_otp_view, name='request_otp'),
    path('verify/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard & Main
    path('', views.dashboard_overview_view, name='dashboard_overview'),

    # Configuration
    path('connect/', views.connect_site_view, name='connect_site'),

    path('products/', views.product_list_view, name='product_list'),
    path('products/<int:pk>/', views.product_detail_view, name='product_detail'),

    # Customer Analytics
    path('customers/<str:identifier>/', views.customer_profile_view, name='customer_profile'),

    # Advanced Analytics
    path('analytics/cohort/', views.cohort_analysis_view, name='cohort_analysis'),

    # A/B Testing
    path('ab-testing/', views.ab_test_list_view, name='ab_test_list'),
    path('ab-testing/new/', views.ab_test_create_view, name='ab_test_create'),
    path('ab-testing/<int:pk>/', views.ab_test_detail_view, name='ab_test_detail'),

    # API Endpoints
    path('api/track-event/', views.track_event_view, name='track_event'),
    path('api/get-variant/', views.get_product_variant_api, name='get_product_variant'),

    # این مسیر جدید را اضافه کنید
    path('api/daily-events-chart/', views.daily_events_chart_api, name='daily_events_chart_api'),
]
