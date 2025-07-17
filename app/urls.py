from django.urls import path

from . import views


app_name = 'app'


urlpatterns = [
    path('OTP_register/', views.OTPRegisterView.as_view()),
    path('OTP_Verify/', views.OTPVerifyAPIView.as_view()),
    path('dashboard/', views.Dashboard.as_view()),

    path('track-event/', views.TrackEventAPIView.as_view()),
    path('recommendations/product/<str:product_source_id>/', views.ProductRecommendationAPIView.as_view(),
         name='product-recommendations'),


    path('products/', views.Product_all.as_view(), name='product_all'),


    #Templates
    path('shop/', views.product_list_view, name='product_list'),
    path('shop/product/<str:product_source_id>/', views.product_detail_view, name='product_detail'),

]
