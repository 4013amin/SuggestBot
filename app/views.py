from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from accounts.models import SubscriptionPlan, UserSubscription, User
from django.contrib.auth import login
from django.shortcuts import render, get_object_or_404
from .models import Product, Order, Recommendation
from django.db.models import Count, Sum


# Create your views here.

def dashboard_view(request):
    """ ویو برای نمایش داشبورد کلی """
    product_count = Product.objects.count()
    order_count = Order.objects.count()
    active_recommendations_count = Recommendation.objects.filter(is_active=True).count()

    # پیدا کردن پرفروش‌ترین محصولات
    top_selling_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:5]

    # پیدا کردن کم‌فروش‌ترین محصولات
    low_selling_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('total_sold')[:5]

    context = {
        'product_count': product_count,
        'order_count': order_count,
        'active_recommendations_count': active_recommendations_count,
        'top_selling_products': top_selling_products,
        'low_selling_products': low_selling_products,
    }
    return render(request, 'app/dashboard.html', context)


def product_detail_view(request, pk):
    """ ویو برای نمایش جزئیات یک محصول خاص """
    product = get_object_or_404(Product, pk=pk)

    # سفارش‌هایی که این محصول در آن‌ها بوده است
    orders_containing_product = Order.objects.filter(products=product).order_by('-created_at')[:10]

    product_recommendations = Recommendation.objects.filter(product=product, is_active=True)

    sales_chart_data = {
        'labels': ['فروردین', 'اردیبهشت', 'خرداد', 'تیر'],
        'data': [12, 19, 3, 5],
    }

    context = {
        'product': product,
        'orders': orders_containing_product,
        'recommendations': product_recommendations,
        'sales_chart_data': sales_chart_data,
    }
    return render(request, 'app/product_detail.html', context)


def recommendations_view(request):
    all_active_recommendations = Recommendation.objects.filter(is_active=True).order_by('-created_at')
    context = {
        'recommendations': all_active_recommendations,
    }
    return render(request, 'app/recommendations.html', context)
