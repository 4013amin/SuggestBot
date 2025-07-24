import random
from django.shortcuts import render, redirect, get_object_or_404  # اصلاح شد
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone  # اضافه شد
from datetime import timedelta  # اضافه شد
from django.db.models import Count, Q  # اضافه شد
from .forms import OTPRequestForm, OTPVerifyForm
from .models import OTPCode, ApiKey, Product, ProductEvent, Recommendation  # اضافه شد


def request_otp_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_overview')  # بهتر است به داشبورد برود

    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            user, created = User.objects.get_or_create(username=phone_number)
            code = str(random.randint(100000, 999999))
            OTPCode.objects.filter(user=user).delete()
            OTPCode.objects.create(user=user, code=code)
            print(f"OTP Code for {phone_number}: {code}")
            request.session['otp_phone_number'] = phone_number
            return redirect('core:verify_otp')
    else:
        form = OTPRequestForm()
    return render(request, 'request_otp.html', {'form': form})  # اصلاح مسیر


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_overview')

    phone_number = request.session.get('otp_phone_number')
    if not phone_number:
        return redirect('core:request_otp')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                user = User.objects.get(username=phone_number)
                otp = OTPCode.objects.get(user=user, code=code)
                if otp.is_valid():
                    login(request, user)
                    otp.delete()
                    del request.session['otp_phone_number']
                    return redirect('core:dashboard_overview')  # بهتر است به داشبورد برود
                else:
                    form.add_error('code', 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')
            except (OTPCode.DoesNotExist, User.DoesNotExist):
                form.add_error('code', 'کد وارد شده صحیح نیست.')
    else:
        form = OTPVerifyForm()
    return render(request, 'verify_otp.html', {'form': form, 'phone_number': phone_number})  # اصلاح مسیر


@login_required
def connect_site_view(request):
    try:
        api_key_obj = ApiKey.objects.get(user=request.user)
    except ApiKey.DoesNotExist:
        api_key_obj = ApiKey.objects.create(user=request.user)
    context = {'api_key': api_key_obj.key}
    return render(request, 'connect_site.html', context)


@login_required
def dashboard_overview_view(request):
    user = request.user
    thirty_days_ago = timezone.now() - timedelta(days=30)
    products = Product.objects.filter(owner=user)
    total_views = ProductEvent.objects.filter(product__in=products, event_type='VIEW',
                                              created_at__gte=thirty_days_ago).count()
    total_add_to_cart = ProductEvent.objects.filter(product__in=products, event_type='ADD_TO_CART',
                                                    created_at__gte=thirty_days_ago).count()
    popular_products = products.annotate(views_count=Count('events', filter=Q(events__event_type='VIEW'))).order_by(
        '-views_count')[:5]
    attention_products = products.annotate(
        views_count=Count('events', filter=Q(events__event_type='VIEW', events__created_at__gte=thirty_days_ago)),
        carts_count=Count('events',
                          filter=Q(events__event_type='ADD_TO_CART', events__created_at__gte=thirty_days_ago))).filter(
        views_count__gt=10, carts_count=0).order_by('-views_count')[:5]
    general_recommendations = Recommendation.objects.filter(owner=user, is_active=True)[:5]
    context = {'total_views': total_views, 'total_add_to_cart': total_add_to_cart, 'product_count': products.count(),
               'popular_products': popular_products, 'attention_products': attention_products,
               'recommendations': general_recommendations}
    return render(request, 'dashboard_overview.html', context)


@login_required
def product_detail_view(request, pk):
    user = request.user
    product = get_object_or_404(Product, pk=pk, owner=user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    views = product.events.filter(event_type='VIEW', created_at__gte=thirty_days_ago).count()
    add_to_carts = product.events.filter(event_type='ADD_TO_CART', created_at__gte=thirty_days_ago).count()
    conversion_rate = (add_to_carts / views * 100) if views > 0 else 0
    chart_labels = []
    chart_views = []
    for i in range(7):
        day = timezone.now() - timedelta(days=i)
        count = product.events.filter(event_type='VIEW', created_at__date=day.date()).count()
        chart_labels.append(day.strftime('%A'))
        chart_views.append(count)
    chart_labels.reverse()
    chart_views.reverse()
    product_recommendations = product.recommendations.filter(is_active=True)
    context = {'product': product, 'views_30_days': views, 'carts_30_days': add_to_carts,
               'conversion_rate': f"{conversion_rate:.2f}", 'chart_labels': chart_labels, 'chart_views': chart_views,
               'recommendations': product_recommendations}
    return render(request, 'product_detail.html', context)
