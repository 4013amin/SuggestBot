import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q
from .forms import OTPRequestForm, OTPVerifyForm
from .models import OTPCode, ApiKey, Product, ProductEvent, Recommendation
from .utils import update_recommendations, fetch_product_data, predict_cart_abandonment
import logging
import random
from django.http import JsonResponse
from .utils import fetch_data_for_analysis, generate_ai_recommendations

logger = logging.getLogger(__name__)

AI_API_URL = "https://api.x.ai/v1/recommendations"  # آدرس API مدل هوش مصنوعی
AI_API_KEY = "your-ai-api-key"  # کلید API (باید از x.ai/api دریافت شود)


@login_required
def dashboard_overview_view(request):
    user = request.user
    end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=29)).strftime('%Y-%m-%d'))

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
        start_date = timezone.make_aware(start_date)
    except (ValueError, TypeError):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=29)

    # به‌روزرسانی پیشنهادات
    update_recommendations(user, start_date, end_date)

    products = Product.objects.filter(owner=user)
    all_events = ProductEvent.objects.filter(product__in=products, created_at__range=(start_date, end_date))
    total_views = all_events.filter(event_type='VIEW').count()
    total_carts = all_events.filter(event_type='ADD_TO_CART').count()
    total_purchases = all_events.filter(event_type='PURCHASE').count()
    overall_conversion = (total_carts / total_views * 100) if total_views > 0 else 0
    overall_purchase_rate = (total_purchases / total_views * 100) if total_views > 0 else 0

    date_filter = Q(events__created_at__range=(start_date, end_date))
    views_in_range = Count('events', filter=Q(events__event_type='VIEW') & date_filter)
    carts_in_range = Count('events', filter=Q(events__event_type='ADD_TO_CART') & date_filter)
    purchases_in_range = Count('events', filter=Q(events__event_type='PURCHASE') & date_filter)

    popular_products = products.annotate(
        views_count=views_in_range,
        carts_count=carts_in_range,
        purchases_count=purchases_in_range
    ).order_by('-purchases_count', '-carts_count', '-views_count')[:5]

    attention_products = products.annotate(
        views_count=views_in_range,
        carts_count=carts_in_range
    ).filter(views_count__gt=20, carts_count=0).order_by('-views_count')[:5]

    latest_recommendations = Recommendation.objects.filter(
        owner=user, is_active=True
    ).order_by('-created_at', '-confidence_score')[:10]

    context = {
        'total_views': total_views,
        'total_carts': total_carts,
        'total_purchases': total_purchases,
        'overall_conversion': f"{overall_conversion:.2f}",
        'overall_purchase_rate': f"{overall_purchase_rate:.2f}",
        'product_count': products.count(),
        'popular_products': popular_products,
        'attention_products': attention_products,
        'recommendations': latest_recommendations,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'is_custom_date_range': 'start_date' in request.GET,
    }
    return render(request, 'dashboard_overview.html', context)


def request_otp_view(request):
    if request.user.is_authenticated:
        logger.info(f"User already authenticated: {request.user.username}")
        return redirect('core:dashboard_overview')

    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            user, created = User.objects.get_or_create(username=phone_number)
            code = str(random.randint(100000, 999999))
            OTPCode.objects.filter(user=user).delete()
            OTPCode.objects.create(user=user, code=code)
            request.session['otp_phone_number'] = phone_number
            logger.info(f"OTP sent: phone={phone_number}, code={code}, user_created={created}")
            return redirect('core:verify_otp')
        else:
            logger.warning(f"Invalid OTP request form: errors={form.errors}")
    else:
        form = OTPRequestForm()
    return render(request, 'request_otp.html', {'form': form})


def verify_otp_view(request):
    if request.user.is_authenticated:
        logger.info(f"User already authenticated: {request.user.username}")
        return redirect('core:dashboard_overview')

    phone_number = request.session.get('otp_phone_number')
    if not phone_number:
        logger.warning("verify_otp_view: no phone_number in session")
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
                    logger.info(f"OTP verified successfully for user: {user.username}")
                    return redirect('core:dashboard_overview')
                else:
                    form.add_error('code', 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')
                    logger.warning(f"Expired OTP for user: {user.username}")
            except (OTPCode.DoesNotExist, User.DoesNotExist):
                form.add_error('code', 'کد وارد شده صحیح نیست.')
                logger.warning(f"Invalid OTP or user not found: phone={phone_number}, code={code}")
        else:
            logger.warning(f"Invalid OTP verification form: errors={form.errors}")
    else:
        form = OTPVerifyForm()
    return render(request, 'verify_otp.html', {'form': form, 'phone_number': phone_number})


@login_required
def connect_site_view(request):
    api_key_obj, created = ApiKey.objects.get_or_create(user=request.user)
    context = {'api_key': api_key_obj.key}
    return render(request, 'connect_site.html', context)


@login_required
def product_detail_view(request, pk):
    user = request.user
    product = get_object_or_404(Product, pk=pk, owner=user)

    thirty_days_ago = timezone.now() - timedelta(days=30)
    views_30_days = product.events.filter(event_type='VIEW', created_at__gte=thirty_days_ago).count()
    carts_30_days = product.events.filter(event_type='ADD_TO_CART', created_at__gte=thirty_days_ago).count()
    purchases_30_days = product.events.filter(event_type='PURCHASE', created_at__gte=thirty_days_ago).count()
    conversion_rate = (carts_30_days / views_30_days * 100) if views_30_days > 0 else 0
    purchase_rate = (purchases_30_days / views_30_days * 100) if views_30_days > 0 else 0

    chart_labels, chart_views, chart_carts, chart_purchases = [], [], [], []
    today = timezone.now()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        views_count = product.events.filter(event_type='VIEW', created_at__date=day.date()).count()
        carts_count = product.events.filter(event_type='ADD_TO_CART', created_at__date=day.date()).count()
        purchases_count = product.events.filter(event_type='PURCHASE', created_at__date=day.date()).count()
        chart_labels.append(day.strftime('%A'))
        chart_views.append(views_count)
        chart_carts.append(carts_count)
        chart_purchases.append(purchases_count)

    product_recommendations = product.core_recommendations.filter(is_active=True).order_by('-confidence_score')

    context = {
        'product': product,
        'views_30_days': views_30_days,
        'carts_30_days': carts_30_days,
        'purchases_30_days': purchases_30_days,
        'conversion_rate': f"{conversion_rate:.2f}",
        'purchase_rate': f"{purchase_rate:.2f}",
        'chart_labels': chart_labels,
        'chart_views': chart_views,
        'chart_carts': chart_carts,
        'chart_purchases': chart_purchases,
        'recommendations': product_recommendations
    }
    return render(request, 'product_detail.html', context)


@login_required
def request_ai_recommendation(request, pk):
    """درخواست پیشنهادات هوش مصنوعی برای یک محصول خاص"""
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # جمع‌آوری داده‌های محصول
    product_data = fetch_product_data(product, thirty_days_ago, timezone.now())

    # درخواست پیشنهادات از API هوش مصنوعی
    generate_ai_recommendations(request.user, product_data)

    # گرفتن پیشنهادات جدید
    recommendations = product.core_recommendations.filter(
        is_active=True, reason='AI_GENERATED'
    ).order_by('-confidence_score')

    # آماده‌سازی داده‌ها برای پاسخ JSON
    recommendations_data = [
        {'text': rec.text, 'confidence_score': rec.confidence_score}
        for rec in recommendations
    ]

    return JsonResponse({'recommendations': recommendations_data})


@login_required
def product_abandonment_view(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    abandonment_score, suggestion = predict_cart_abandonment(request.user, product, thirty_days_ago, timezone.now())
    context = {
        'product': product,
        'abandonment_score': f"{abandonment_score:.2f}",
        'suggestion': suggestion,
        'error': None if abandonment_score else "خطا در دریافت پیش‌بینی ترک سبد خرید. لطفاً بعداً تلاش کنید."
    }
    return render(request, 'product_abandonment.html', context)


# تحلیل رقبا
@login_required
def competitor_comparison_view(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    try:
        headers = {'Authorization': f'Bearer {AI_API_KEY}'}
        response = requests.get(f"{AI_API_URL}/competitor_data", json={'product_name': product.name}, headers=headers)
        competitor_data = response.json().get('competitors', [])
    except requests.RequestException:
        competitor_data = []
    context = {'product': product, 'competitor_data': competitor_data}
    return render(request, 'competitor_comparison.html', context)


# Chat_with AI
@login_required
def ai_chat_recommendation(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    if request.method == 'POST':
        question = request.POST.get('question')
        product_data = fetch_product_data(product, timezone.now() - timedelta(days=30), timezone.now())
        try:
            headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
            response = requests.post(f"{AI_API_URL}/chat", json={'question': question, 'product': product_data},
                                     headers=headers)
            response.raise_for_status()
            answer = response.json().get('answer', 'پاسخی دریافت نشد.')
        except requests.RequestException:
            answer = 'خطا در دریافت پاسخ از هوش مصنوعی.'
        return JsonResponse({'answer': answer})
    return JsonResponse({'error': 'فقط درخواست‌های POST مجاز هستند'}, status=400)


# دانلود با PDF
@login_required
def product_report_pdf(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    product_data = fetch_product_data(product, thirty_days_ago, timezone.now())
    recommendations = product.core_recommendations.filter(is_active=True).order_by('-confidence_score')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{product.name}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    pdfmetrics.registerFont(TTFont('Vazir', 'path/to/Vazir.ttf'))  # مسیر فونت Vazir
    p.setFont('Vazir', 12)

    y = 800
    p.drawString(100, y, f"گزارش محصول: {product.name}")
    y -= 30
    p.drawString(100, y, f"بازدید 30 روز: {product_data['views']}")
    y -= 20
    p.drawString(100, y, f"افزودن به سبد: {product_data['carts']}")
    y -= 20
    p.drawString(100, y, f"خرید: {product_data['purchases']}")
    y -= 20
    p.drawString(100, y, f"نرخ تبدیل: {product_data['conversion_rate']:.2f}%")
    y -= 30
    p.drawString(100, y, "پیشنهادات:")
    for rec in recommendations:
        y -= 20
        p.drawString(100, y, f"- {rec.text} ({'هوش مصنوعی' if rec.reason == 'AI_GENERATED' else 'تحلیل سیستم'})")
    p.showPage()
    p.save()
    return response


def logout(request):
    auth_logout(request)
    return redirect('core:request_otp')
