from django.urls import path
from . import views


app_name = 'app'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    # path('api/sync/', views.SyncDataView.as_view(), name='api_sync_data'),
]