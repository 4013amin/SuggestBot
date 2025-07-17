from django.urls import path

from . import views

urlpatterns = [
    path('OTP_register/', views.OTPRegisterView.as_view()),
    path('OTP_Verify/', views.OTPVerifyAPIView.as_view()),
    path('dashboard/', views.Dashboard.as_view()),

    path('track-event/', views.TrackEventAPIView.as_view()),
    path('recommendations/product/<str:product_source_id>/', views.ProductRecommendationAPIView.as_view(),
         name='product-recommendations'),
]
