# subscription_frontend/urls.py

from django.urls import path
from . import views

app_name = 'subscription_frontend'

urlpatterns = [
    path('dashboard/', views.subscription_dashboard_view, name='dashboard'),
    path('purchase/<int:plan_id>/', views.purchase_confirmation_view, name='purchase_confirmation'),
    path('login/', views.dummy_login_view, name='dummy_login'),
]
