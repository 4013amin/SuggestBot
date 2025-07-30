# core/views.py

import logging
import random
import json
from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    Product, ProductEvent, Recommendation, OTPCode, UserSite, ApiKey,
    Customer, ABTest, ABTestEvent
)
from .forms import OTPRequestForm, OTPVerifyForm, ABTestForm
from .utils import (
    calculate_funnel_analysis, get_customer_segments, get_market_basket_analysis,
    predict_future_sales, get_ab_test_results, get_cohort_analysis
)

logger = logging.getLogger(__name__)


@login_required
def dashboard_overview_view(request):
    """نمایش داشبورد اصلی با آمار کلی و تحلیل‌های پیشرفته."""
    user = request.user
    try:
        end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
        start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=6)).strftime('%Y-%m-%d'))
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

    aware_start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    aware_end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    date_range = (aware_start_date, aware_end_date)

    products = Product.objects.filter(owner=user)
    all_events = ProductEvent.objects.filter(product__in=products, created_at__range=date_range)
    total_views = all_events.filter(event_type='VIEW').count()
    total_carts = all_events.filter(event_type='ADD_TO_CART').count()
    total_purchases = all_events.filter(event_type='PURCHASE').count()
    overall_conversion = (total_purchases / total_views * 100) if total_views > 0 else 0

    popular_products = products.annotate(
        purchases_count=Count('events', filter=Q(events__event_type='PURCHASE', events__created_at__range=date_range))
    ).filter(purchases_count__gt=0).order_by('-purchases_count')[:5]

    recommendations = Recommendation.objects.filter(owner=user, is_active=True).order_by('-created_at')[:5]

    funnel_data = calculate_funnel_analysis(user, aware_start_date, aware_end_date)
    customer_segments = get_customer_segments(user, aware_start_date, aware_end_date)
    market_basket_df, market_basket_message = get_market_basket_analysis(user)

    # تبدیل دیتافریم به لیست دیکشنری‌ها برای تمپلیت
    market_basket_rules = market_basket_df.to_dict('records') if market_basket_df is not None else []

    # پیش‌بینی فروش (این بخش اضافه شد)
    sales_forecast, forecast_message, forecast_product_name = None, "محصول پرفروشی برای پیش‌بینی یافت نشد.", ""
    top_product = ProductEvent.objects.filter(product__owner=user, event_type='PURCHASE'
                                              ).values('product__id', 'product__name').annotate(c=Count('id')).order_by(
        '-c').first()

    if top_product:
        forecast_product_name = top_product['product__name']
        sales_forecast, forecast_message = predict_future_sales(top_product['product__id'])

    context = {
        'total_views': total_views,
        'total_carts': total_carts,
        'total_purchases': total_purchases,
        'overall_conversion': f"{overall_conversion:.2f}",
        'popular_products': popular_products,
        'recommendations': recommendations,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'funnel_data': funnel_data,
        'customer_segments': customer_segments,
        'market_basket_rules': market_basket_rules,
        'market_basket_message': market_basket_message,
        'sales_forecast': sales_forecast,
        'forecast_message': forecast_message,
        'forecast_product_name': forecast_product_name,
    }
    return render(request, 'dashboard_overview.html', context)


@login_required
def daily_events_chart_api(request):
    """API جدید برای تامین داده‌های نمودار داینامیک داشبورد."""
    user = request.user
    try:
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    except (ValueError, TypeError, AttributeError):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

    date_range_labels = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    chart_data = {d.strftime('%Y-%m-%d'): {'views': 0, 'carts': 0, 'purchases': 0} for d in date_range_labels}

    events_by_day = ProductEvent.objects.filter(
        product__owner=user, created_at__date__range=(start_date, end_date)
    ).annotate(day=TruncDate('created_at')).values('day', 'event_type').annotate(count=Count('id'))

    for event in events_by_day:
        day_str = event['day'].strftime('%Y-%m-%d')
        if event['event_type'] == 'VIEW':
            chart_data[day_str]['views'] = event['count']
        elif event['event_type'] == 'ADD_TO_CART':
            chart_data[day_str]['carts'] = event['count']
        elif event['event_type'] == 'PURCHASE':
            chart_data[day_str]['purchases'] = event['count']

    return JsonResponse({
        'labels': list(chart_data.keys()),
        'views': [d['views'] for d in chart_data.values()],
        'carts': [d['carts'] for d in chart_data.values()],
        'purchases': [d['purchases'] for d in chart_data.values()],
    })


def request_otp_view(request):
    """ارسال کد یکبار مصرف برای ورود کاربر."""
    if request.user.is_authenticated:
        return redirect('core:dashboard_overview')
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            user, _ = User.objects.get_or_create(username=phone_number)
            code = str(random.randint(100000, 999999))
            OTPCode.objects.filter(user=user).delete()
            OTPCode.objects.create(user=user, code=code)
            request.session['otp_phone_number'] = phone_number
            logger.info(f"OTP sent: phone={phone_number}, code={code}")  # کد در عمل نباید لاگ شود
            return redirect('core:verify_otp')
    else:
        form = OTPRequestForm()
    return render(request, 'request_otp.html', {'form': form})


def verify_otp_view(request):
    """تایید کد یکبار مصرف و ورود کاربر."""
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
                    return redirect('core:dashboard_overview')
                else:
                    form.add_error('code', 'کد منقضی شده است.')
            except (OTPCode.DoesNotExist, User.DoesNotExist):
                form.add_error('code', 'کد وارد شده صحیح نیست.')
    else:
        form = OTPVerifyForm()
    return render(request, 'verify_otp.html', {'form': form, 'phone_number': phone_number})


@login_required
def connect_site_view(request):
    """نمایش کلید API و راهنمای اتصال سایت."""
    api_key_obj, _ = ApiKey.objects.get_or_create(user=request.user)
    UserSite.objects.get_or_create(
        owner=request.user,
        api_key=api_key_obj,
        defaults={'site_url': f'https://my-site-{request.user.username}.com'}
    )
    context = {'api_key': api_key_obj.key}
    return render(request, 'connect_site.html', context)


@csrf_exempt
@require_POST
def track_event_view(request):
    """API دریافت رویدادها از سایت کاربر."""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return JsonResponse({'error': 'API Key required'}, status=401)
    try:
        site = UserSite.objects.select_related('owner').get(api_key__key=api_key, is_active=True)
    except UserSite.DoesNotExist:
        return JsonResponse({'error': 'Invalid or inactive API Key'}, status=401)

    try:
        data = json.loads(request.body)
        event_type = data['event_type']
        product_data = data['product']
        customer_identifier = data.get('customer_id') or request.META.get('REMOTE_ADDR')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if event_type not in ['VIEW', 'ADD_TO_CART', 'PURCHASE']:
        return JsonResponse({'error': 'Invalid event type'}, status=400)

    product, _ = Product.objects.update_or_create(
        owner=site.owner,
        product_id_from_site=product_data['id'],
        defaults={
            'name': product_data.get('name', 'محصول ناشناس'),
            'price': Decimal(str(product_data.get('price', 0))),
            'page_url': product_data.get('url', ''),
        }
    )

    customer, _ = Customer.objects.get_or_create(owner=site.owner, identifier=customer_identifier)

    event = ProductEvent.objects.create(product=product, customer=customer, event_type=event_type)

    # بررسی تست A/B و ثبت رویداد مربوطه
    if 'ab_test_variant' in data and data['ab_test_variant']:
        try:
            test = ABTest.objects.get(id=data['ab_test_id'], is_active=True)
            event_type_map = {'PURCHASE': 'CONVERSION', 'VIEW': 'VIEW'}
            if event.event_type in event_type_map:
                ABTestEvent.objects.create(
                    test=test,
                    customer=customer,
                    variant_shown=data['ab_test_variant'],
                    event_type=event_type_map[event.event_type]
                )
        except ABTest.DoesNotExist:
            logger.warning(f"A/B Test with id {data.get('ab_test_id')} not found.")

    return JsonResponse({'status': 'success', 'event_id': event.id})


@csrf_exempt
def get_product_variant_api(request):
    """API برای تعیین نسخه محصول در تست A/B."""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return JsonResponse({'error': 'API Key required'}, status=401)

    try:
        data = json.loads(request.body)
        product_id_from_site = data.get('product_id')
        customer_identifier = data.get('customer_id') or request.META.get('REMOTE_ADDR')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    try:
        product = Product.objects.get(product_id_from_site=product_id_from_site, owner__sites__api_key__key=api_key)
        active_test = ABTest.objects.filter(product=product, is_active=True).first()

        if active_test:
            # تقسیم کاربران به دو گروه (کنترل و متغیر)
            variant_type = 'VARIANT' if hash(customer_identifier) % 2 == 0 else 'CONTROL'

            if variant_type == 'VARIANT':
                return JsonResponse({
                    'ab_test_id': active_test.id,
                    'ab_test_variant': 'VARIANT',
                    'variable': active_test.variable,
                    'value': active_test.variant_value
                })

    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    # اگر تستی فعال نباشد یا کاربر در گروه کنترل باشد
    return JsonResponse({'ab_test_id': None})


@login_required
def ab_test_list_view(request):
    """نمایش لیست تمام تست‌های A/B."""
    tests = ABTest.objects.filter(product__owner=request.user).select_related('product').order_by('-is_active',
                                                                                                  '-start_date')
    return render(request, 'ab_test_list.html', {'tests': tests})


@login_required
def ab_test_create_view(request):
    """ایجاد یک تست A/B جدید."""
    if request.method == 'POST':
        form = ABTestForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('core:ab_test_list')
    else:
        form = ABTestForm(user=request.user)
    return render(request, 'ab_test_form.html', {'form': form})


@login_required
def ab_test_detail_view(request, pk):
    """نمایش جزئیات و نتایج یک تست A/B."""
    test = get_object_or_404(ABTest, pk=pk, product__owner=request.user)
    results = get_ab_test_results(test)
    context = {
        'test': test,
        'results': results,
    }
    return render(request, 'ab_test_detail.html', context)


@login_required
def cohort_analysis_view(request):
    """نمایش تحلیل کوهورت (بازگشت مشتری)."""
    cohort_table, message = get_cohort_analysis(request.user)
    context = {
        'cohort_table_html': cohort_table.to_html(classes='table table-bordered text-center', na_rep=''),
        'message': message
    }
    return render(request, 'cohort_analysis.html', context)


@login_required
def customer_profile_view(request, identifier):
    """نمایش پروفایل کامل یک مشتری."""
    customer = get_object_or_404(Customer, identifier=identifier, owner=request.user)
    events = customer.events.select_related('product').order_by('-created_at')

    total_spent = events.filter(event_type='PURCHASE').aggregate(total=Sum('product__price'))['total'] or 0
    purchase_count = events.filter(event_type='PURCHASE').count()

    context = {
        'customer': customer,
        'events': events,
        'total_spent': total_spent,
        'purchase_count': purchase_count,
        'event_count': events.count()
    }
    return render(request, 'customer_profile.html', context)


@login_required
def product_list_view(request):
    """نمایش لیستی از تمام محصولات کاربر."""
    products = Product.objects.filter(owner=request.user).order_by('-created_at')
    context = {
        'products': products
    }
    return render(request, 'product_list.html', context)

@login_required
def product_detail_view(request, pk):
    """نمایش آمار و تحلیل‌های جامع برای یک محصول خاص."""
    product = get_object_or_404(Product, pk=pk, owner=request.user)

    # بازه زمانی پیش‌فرض: ۳۰ روز گذشته
    end_date = timezone.now()
    start_date = end_date - timedelta(days=29)

    events = product.events.filter(created_at__range=(start_date, end_date))

    # ۱. آمار کلیدی
    views_30_days = events.filter(event_type='VIEW').count()
    carts_30_days = events.filter(event_type='ADD_TO_CART').count()
    purchases_30_days = events.filter(event_type='PURCHASE').count()

    # ۲. نرخ‌های تبدیل
    # نرخ تبدیل بازدید به سبد خرید
    view_to_cart_rate = (carts_30_days / views_30_days * 100) if views_30_days > 0 else 0
    # نرخ تبدیل بازدید به خرید نهایی
    view_to_purchase_rate = (purchases_30_days / views_30_days * 100) if views_30_days > 0 else 0

    # ۳. داده‌های نمودار برای ۷ روز گذشته
    chart_labels = []
    chart_views = []
    chart_carts = []
    chart_purchases = []
    today = timezone.now().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_events = product.events.filter(created_at__date=day)

        # لیبل شمسی برای نمودار
        chart_labels.append(jdatetime.date.fromgregorian(date=day).strftime('%a'))
        chart_views.append(day_events.filter(event_type='VIEW').count())
        chart_carts.append(day_events.filter(event_type='ADD_TO_CART').count())
        chart_purchases.append(day_events.filter(event_type='PURCHASE').count())

    # ۴. پیشنهادات مخصوص این محصول
    product_recommendations = Recommendation.objects.filter(product=product, is_active=True).order_by(
        '-confidence_score')

    # ۵. پیش‌بینی فروش برای این محصول
    sales_forecast, forecast_message = predict_future_sales(product.id)

    context = {
        'product': product,
        'views_30_days': views_30_days,
        'carts_30_days': carts_30_days,
        'purchases_30_days': purchases_30_days,
        'view_to_cart_rate': f"{view_to_cart_rate:.1f}",
        'view_to_purchase_rate': f"{view_to_purchase_rate:.1f}",
        'chart_labels': json.dumps(chart_labels),
        'chart_views': json.dumps(chart_views),
        'chart_carts': json.dumps(chart_carts),
        'chart_purchases': json.dumps(chart_purchases),
        'recommendations': product_recommendations,
        'sales_forecast': sales_forecast,
        'forecast_message': forecast_message,
    }
    return render(request, 'products/product_detail.html', context)





def logout_view(request):
    """خروج کاربر از سیستم."""
    auth_logout(request)
    return redirect('core:request_otp')
