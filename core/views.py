import io
import os
from decimal import Decimal
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
from arabic_reshaper import arabic_reshaper
from bidi import get_display
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, F, ExpressionWrapper, fields, Case, When
from django.db.models.functions import TruncDate
from matplotlib import pyplot as plt
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from rest_framework.utils import json
import csv
import numpy as np

from .forms import OTPRequestForm, OTPVerifyForm
from .models import OTPCode, ApiKey, Product, ProductEvent, Recommendation, \
    UserSite  # توجه: ممکن است نیاز به افزودن مدل Webhook داشته باشید
from .utils import update_recommendations, fetch_product_data, predict_cart_abandonment
import logging
import random
from django.http import JsonResponse, HttpResponse
from .utils import fetch_data_for_analysis, generate_ai_recommendations
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

AI_API_URL = "https://api.x.ai/v1/recommendations"
AI_API_KEY = "your-ai-api-key"


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
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    product_data = fetch_product_data(product, thirty_days_ago, timezone.now())
    generate_ai_recommendations(request.user, product_data)
    recommendations = product.core_recommendations.filter(
        is_active=True, reason='AI_GENERATED'
    ).order_by('-confidence_score')
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


def prepare_rtl_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


@login_required
def product_report_pdf(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    views_30_days = product.events.filter(event_type='VIEW', created_at__gte=thirty_days_ago).count()
    carts_30_days = product.events.filter(event_type='ADD_TO_CART', created_at__gte=thirty_days_ago).count()
    purchases_30_days = product.events.filter(event_type='PURCHASE', created_at__gte=thirty_days_ago).count()
    conversion_rate = (carts_30_days / views_30_days * 100) if views_30_days > 0 else 0
    purchase_rate = (purchases_30_days / views_30_days * 100) if views_30_days > 0 else 0

    today = timezone.now()
    chart_labels_fa = []
    chart_views, chart_carts, chart_purchases = [], [], []
    days_map = {'Saturday': 'شنبه', 'Sunday': 'یکشنبه', 'Monday': 'دوشنبه',
                'Tuesday': 'سه‌شنبه', 'Wednesday': 'چهارشنبه', 'Thursday': 'پنج‌شنبه', 'Friday': 'جمعه'}

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_name_en = day.strftime('%A')
        chart_labels_fa.append(days_map.get(day_name_en, day_name_en))
        chart_views.append(product.events.filter(event_type='VIEW', created_at__date=day.date()).count())
        chart_carts.append(product.events.filter(event_type='ADD_TO_CART', created_at__date=day.date()).count())
        chart_purchases.append(product.events.filter(event_type='PURCHASE', created_at__date=day.date()).count())

    recommendations = product.core_recommendations.filter(is_active=True).order_by('-confidence_score')

    fig, ax = plt.subplots(figsize=(10, 5))
    bar_width = 0.25
    index = range(len(chart_labels_fa))
    ax.bar([i - bar_width for i in index], chart_views, bar_width, label='بازدید', color='#4e73df')
    ax.bar(index, chart_carts, bar_width, label='سبد خرید', color='#1cc88a')
    ax.bar([i + bar_width for i in index], chart_purchases, bar_width, label='خرید', color='#e74a3b')
    ax.set_ylabel('تعداد رویداد')
    ax.set_title('آمار عملکرد در ۷ روز گذشته')
    ax.set_xticks(list(index))
    ax.set_xticklabels(chart_labels_fa)
    ax.legend()
    fig.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300)
    buffer.seek(0)
    plt.close(fig)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{product.name}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    font_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'fonts', 'Vazirmatn-Black.ttf')
    pdfmetrics.registerFont(TTFont('Vazir', font_path))
    styles = getSampleStyleSheet()
    style_right = ParagraphStyle(name='PersianRight', parent=styles['Normal'], fontName='Vazir', alignment=TA_RIGHT,
                                 fontSize=12, leading=20)
    style_title = ParagraphStyle(name='PersianTitle', parent=style_right, fontSize=18, leading=30)

    y = height - 1.5 * cm
    margin_right = width - 2 * cm
    title = prepare_rtl_text(f"گزارش جامع محصول: {product.name}")
    p.setFont('Vazir', 18)
    p.drawRightString(margin_right, y, title)
    y -= 1.5 * cm

    stats_title = prepare_rtl_text("آمار کلیدی (۳۰ روز گذشته)")
    p.setFont('Vazir', 14)
    p.drawRightString(margin_right, y, stats_title)
    y -= 1 * cm
    stats_text = f"""
    تعداد بازدید: {views_30_days}<br/>
    تعداد افزودن به سبد خرید: {carts_30_days}<br/>
    تعداد خرید موفق: {purchases_30_days}<br/>
    نرخ تبدیل: {conversion_rate:.2f}%<br/>
    نرخ خرید نهایی: {purchase_rate:.2f}%
    """
    stats_paragraph = Paragraph(prepare_rtl_text(stats_text), style_right)
    stats_paragraph.wrapOn(p, width - 4 * cm, height)
    stats_paragraph.drawOn(p, 2 * cm, y - stats_paragraph.height)
    y -= (stats_paragraph.height + 1 * cm)

    chart_title = prepare_rtl_text("نمودار عملکرد هفتگی")
    p.setFont('Vazir', 14)
    p.drawRightString(margin_right, y, chart_title)
    y -= 7 * cm
    image = ImageReader(buffer)
    p.drawImage(image, x=1.5 * cm, y=y, width=18 * cm, height=6 * cm, preserveAspectRatio=True)
    buffer.close()
    y -= 1 * cm

    recommendations_title = prepare_rtl_text("پیشنهادات بهبود")
    p.setFont('Vazir', 14)
    p.drawRightString(margin_right, y, recommendations_title)
    y -= 1 * cm
    if recommendations:
        for rec in recommendations:
            rec_type = 'هوش مصنوعی' if rec.reason == 'AI_GENERATED' else 'تحلیل سیستم'
            text = f"- {rec.text} <b>(نوع: {rec_type} | اطمینان: {rec.confidence_score:.0%})</b>"
            paragraph = Paragraph(prepare_rtl_text(text), style_right)
            paragraph.wrapOn(p, width - 4 * cm, height)
            if y - paragraph.height < 1.5 * cm:
                p.showPage()
                p.setFont('Vazir', 12)
                y = height - 1.5 * cm
            paragraph.drawOn(p, 2 * cm, y - paragraph.height)
            y -= (paragraph.height + 0.2 * cm)
    else:
        no_rec = prepare_rtl_text("در حال حاضر پیشنهاد فعالی برای این محصول وجود ندارد.")
        p.drawRightString(margin_right - 1 * cm, y, no_rec)
    p.showPage()
    p.save()
    return response


@cache_control(max_age=3600)
def tracking_script_view(request):
    js_content = """
    (function() {
        var apiKey = document.currentScript.getAttribute('data-api-key');
        if (!apiKey) {
            console.error('API Key not provided for tracking script.');
            return;
        }

        function sendEvent(eventType, productData) {
            fetch('https://yourdomain.com/api/track-event/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({
                    event_type: eventType,
                    product: productData,
                    timestamp: new Date().toISOString()
                })
            }).catch(error => console.error('Error sending event:', error));
        }

        if (window.location.pathname.includes('/product/')) {
            var product = {
                id: document.querySelector('[data-product-id]')?.dataset.productId || window.location.pathname.split('/').pop(),
                name: document.querySelector('[data-product-name]')?.dataset.productName || document.title,
                price: parseFloat(document.querySelector('[data-product-price]')?.dataset.productPrice) || 0,
                url: window.location.href
            };
            sendEvent('VIEW', product);
        }

        document.addEventListener('click', function(e) {
            if (e.target.closest('[data-add-to-cart]') || e.target.classList.contains('add-to-cart')) {
                var product = {
                    id: e.target.closest('[data-product-id]')?.dataset.productId || window.location.pathname.split('/').pop(),
                    name: e.target.closest('[data-product-name]')?.dataset.productName || document.title,
                    price: parseFloat(e.target.closest('[data-product-price]')?.dataset.productPrice) || 0,
                    url: window.location.href
                };
                sendEvent('ADD_TO_CART', product);
            }
        });

        if (window.location.pathname.includes('/checkout/success') || window.location.pathname.includes('/thank-you')) {
            var products = Array.from(document.querySelectorAll('[data-purchase-item]')).map(item => ({
                id: item.dataset.productId || item.id,
                name: item.dataset.productName || item.querySelector('.product-name')?.textContent,
                price: parseFloat(item.dataset.productPrice) || 0,
                url: item.dataset.productUrl || window.location.href
            }));
            products.forEach(product => sendEvent('PURCHASE', product));
        }
    })();
    """
    return HttpResponse(js_content, content_type='application/javascript')


def send_purchase_webhook(product_event):
    """
    تابع کمکی برای ارسال اطلاعات خرید به یک سرویس خارجی از طریق Webhook.
    این تابع باید پس از ثبت رویداد خرید فراخوانی شود.
    برای این بخش نیاز به مدلی برای ذخیره URL های Webhook دارید.
    """
    user = product_event.product.owner
    # webhooks = Webhook.objects.filter(owner=user, event_type='PURCHASE', is_active=True)

    # کد زیر به صورت شبیه‌سازی شده است (در عمل باید از دیتابیس خوانده شود)
    webhooks = []  # مثال: [{'target_url': 'https://example.com/webhook-receiver'}]

    if not webhooks:
        return

    payload = {
        'product_name': product_event.product.name,
        'product_id': product_event.product.id,
        'price': float(product_event.product.price),
        'purchase_time': product_event.created_at.isoformat(),
        'customer_id': user.username
    }

    for webhook in webhooks:
        try:
            requests.post(webhook.get('target_url'), json=payload, timeout=5)
            logger.info(f"Webhook sent for purchase of {product_event.product.name} to {webhook.get('target_url')}")
        except requests.RequestException as e:
            logger.error(f"Failed to send webhook to {webhook.get('target_url')}: {e}")


@csrf_exempt
@require_POST
def track_event_view(request):
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        logger.warning("Track event: No API Key provided")
        return JsonResponse({'error': 'API Key required'}, status=401)
    try:
        site = UserSite.objects.get(api_key__key=api_key, is_active=True)
    except UserSite.DoesNotExist:
        logger.warning(f"Track event: Invalid or inactive API Key: {api_key}")
        return JsonResponse({'error': 'Invalid or inactive API Key'}, status=401)
    try:
        data = json.loads(request.body)
        event_type = data['event_type']
        product_data = data['product']
        timestamp = data.get('timestamp')
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Track event: Invalid data - {str(e)}")
        return JsonResponse({'error': 'Invalid data'}, status=400)
    if event_type not in ['VIEW', 'ADD_TO_CART', 'PURCHASE']:
        logger.warning(f"Track event: Invalid event type: {event_type}")
        return JsonResponse({'error': 'Invalid event type'}, status=400)

    product, created = Product.objects.update_or_create(
        owner=site.owner,
        product_id_from_site=product_data['id'],
        defaults={
            'name': product_data.get('name', 'محصول ناشناس'),
            'price': Decimal(str(product_data.get('price', 0))),
            'page_url': product_data['url'],
            'category': product_data.get('category', 'عمومی')
        }
    )

    event = ProductEvent.objects.create(
        product=product,
        event_type=event_type,
        created_at=timestamp or timezone.now()
    )

    # فراخوانی وب‌هوک در صورت ثبت خرید
    if event.event_type == 'PURCHASE':
        send_purchase_webhook(event)

    logger.info(f"Event tracked: {event_type} for product {product.name} on site {site.site_url}")
    return JsonResponse({'status': 'success'})


@login_required
def send_dashboard_link_view(request):
    user = request.user
    dashboard_url = request.build_absolute_uri(redirect('core:dashboard_overview').url)
    try:
        send_mail(
            subject='لینک پنل تحلیل فروشگاه شما',
            message=f'برای مشاهده تحلیل‌های فروشگاه‌تون به این لینک بروید:\n{dashboard_url}\n'
                    f'با شماره {user.username} و کد OTP وارد شوید.',
            from_email='from@yourdomain.com',
            recipient_list=[user.email or 'user@example.com'],
            fail_silently=False,
        )
        messages.success(request, 'لینک پنل با موفقیت به ایمیل شما ارسال شد.')
        logger.info(f"Dashboard link sent to {user.username} at {user.email}")
    except Exception as e:
        messages.error(request, 'خطا در ارسال ایمیل. لطفاً با پشتیبانی تماس بگیرید.')
        logger.error(f"Failed to send dashboard link to {user.username}: {str(e)}")
    return redirect('core:dashboard_overview')


def logout(request):
    auth_logout(request)
    return redirect('core:request_otp')


# ===================================================================
# ===== بخش جدید: ویژگی‌های اضافه شده بر اساس درخواست شما =====
# ===================================================================

# بخش جدید: داشبورد پیشرفته با قابلیت‌های بیشتر
@login_required
def advanced_dashboard_view(request):
    """
    این ویو یک داشبورد پیشرفته‌تر با کارت‌های اطلاعاتی جدید و خلاصه‌ای از تحلیل‌ها ارائه می‌دهد.
    """
    user = request.user
    end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=29)).strftime('%Y-%m-%d'))

    try:
        end_date = timezone.make_aware(
            datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
    except (ValueError, TypeError):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=29)

    products = Product.objects.filter(owner=user)
    all_events = ProductEvent.objects.filter(product__in=products, created_at__range=(start_date, end_date))
    total_purchases = all_events.filter(event_type='PURCHASE').count()
    total_revenue = all_events.filter(event_type='PURCHASE').aggregate(
        total=Sum('product__price')
    )['total'] or Decimal('0.00')

    total_categories = products.values('category').distinct().count()
    low_stock_products_count = products.filter(stock__lt=10, stock__gt=0).count()
    out_of_stock_products_count = products.filter(stock=0).count()

    context = {
        'total_revenue': f"{total_revenue:.2f}",
        'total_purchases': total_purchases,
        'total_categories': total_categories,
        'low_stock_products_count': low_stock_products_count,
        'out_of_stock_products_count': out_of_stock_products_count,
        'product_count': products.count(),
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'is_custom_date_range': 'start_date' in request.GET,
    }
    return render(request, 'advanced_dashboard.html', context)


# بخش جدید: تحلیل دسته‌بندی‌ها و پیش‌بینی فروش
@login_required
def category_analysis_view(request):
    """
    این ویو عملکرد هر دسته‌بندی را تحلیل کرده و فروش آینده را به صورت ساده پیش‌بینی می‌کند.
    """
    user = request.user
    end_date = timezone.now()
    start_date = end_date - timedelta(days=29)

    category_data = Product.objects.filter(owner=user).values('category').annotate(
        total_products=Count('id'),
        total_purchases=Count('events', filter=Q(events__event_type='PURCHASE',
                                                 events__created_at__range=(start_date, end_date))),
        total_revenue=Sum('events__product__price',
                          filter=Q(events__event_type='PURCHASE', events__created_at__range=(start_date, end_date)))
    ).order_by('-total_revenue')

    top_category = category_data.first()
    forecast_data = None
    if top_category and top_category['category']:
        daily_sales = ProductEvent.objects.filter(
            product__owner=user,
            product__category=top_category['category'],
            event_type='PURCHASE',
            created_at__gte=start_date
        ).annotate(day=TruncDate('created_at')).values('day').annotate(
            daily_sales_count=Count('id')
        ).order_by('day')

        if len(daily_sales) >= 7:
            last_7_days_sales = [s['daily_sales_count'] for s in daily_sales[len(daily_sales) - 7:]]
            avg_sales = np.mean(last_7_days_sales) if last_7_days_sales else 0
            forecast_data = {
                'category_name': top_category['category'],
                'next_7_days_prediction': int(avg_sales * 7)
            }

    context = {
        'category_data': category_data,
        'forecast_data': forecast_data,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'category_analysis.html', context)


# بخش جدید: نمایش و مرتب‌سازی محصولات بر اساس معیارها
@login_required
def product_list_sorted_view(request):
    """
    این ویو به کاربر اجازه می‌دهد محصولات را بر اساس معیارهای مختلف مشاهده و مرتب کند.
    """
    user = request.user
    sort_by = request.GET.get('sort_by', '-created_at')

    products_qs = Product.objects.filter(owner=user)

    if sort_by == 'highest_discount':
        products = products_qs.order_by('-discount')
    elif sort_by == 'most_purchased':
        products = products_qs.annotate(
            purchase_count=Count('events', filter=Q(events__event_type='PURCHASE'))).order_by('-purchase_count')
    elif sort_by == 'lowest_stock':
        products = products_qs.order_by('stock')
    elif sort_by == 'highest_price':
        products = products_qs.order_by('-price')
    elif sort_by == 'lowest_price':
        products = products_qs.order_by('price')
    else:
        products = products_qs.order_by('-created_at')

    context = {
        'products': products,
        'current_sort': sort_by
    }
    return render(request, 'product_list_sorted.html', context)


# بخش جدید: API برای نمودارهای تعاملی (مثال: نمودار فروش روزانه)
@login_required
def daily_sales_chart_api(request):
    """
    این ویو داده‌های فروش روزانه را در فرمت JSON برای استفاده در نمودارهای JavaScript فراهم می‌کند.
    """
    user = request.user
    end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=29)).strftime('%Y-%m-%d'))

    try:
        end_date = timezone.make_aware(
            datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
    except (ValueError, TypeError):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=29)

    sales_data = ProductEvent.objects.filter(
        product__owner=user,
        event_type='PURCHASE',
        created_at__range=(start_date, end_date)
    ).annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        total_sales=Sum('product__price'),
        count=Count('id')
    ).order_by('day')

    labels = [item['day'].strftime('%Y-%m-%d') for item in sales_data]
    revenue_data = [float(item['total_sales']) for item in sales_data]
    count_data = [item['count'] for item in sales_data]

    data = {
        'labels': labels,
        'revenue_data': revenue_data,
        'count_data': count_data,
    }
    return JsonResponse(data)


# بخش جدید: مرکز اعلان‌ها
@login_required
def notifications_view(request):
    """
    این ویو اعلان‌های مهم مانند اتمام موجودی یا نیاز به توجه را به کاربر نمایش می‌دهد.
    """
    user = request.user

    out_of_stock_products = Product.objects.filter(owner=user, stock=0)
    low_stock_products = Product.objects.filter(owner=user, stock__gt=0, stock__lt=10)

    thirty_days_ago = timezone.now() - timedelta(days=30)
    attention_products = Product.objects.filter(owner=user).annotate(
        views_count=Count('events', filter=Q(events__event_type='VIEW', events__created_at__gte=thirty_days_ago)),
        carts_count=Count('events', filter=Q(events__event_type='ADD_TO_CART', events__created_at__gte=thirty_days_ago))
    ).filter(views_count__gt=50, carts_count=0).order_by('-views_count')

    context = {
        'out_of_stock_products': out_of_stock_products,
        'low_stock_products': low_stock_products,
        'attention_products': attention_products,
    }
    return render(request, 'notifications.html', context)


# بخش جدید: گزارش‌های قابل دانلود (مثال: گزارش فروش در فرمت CSV)
@login_required
def download_sales_report_csv(request):
    """
    این ویو یک گزارش کامل از رویدادهای فروش در بازه زمانی مشخص را در قالب فایل CSV ارائه می‌دهد.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['نام محصول', 'دسته بندی', 'قیمت', 'نوع رویداد', 'تاریخ و زمان'])

    user = request.user
    end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=29)).strftime('%Y-%m-%d'))

    try:
        end_date = timezone.make_aware(
            datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
    except (ValueError, TypeError):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=29)

    events = ProductEvent.objects.filter(
        product__owner=user,
        created_at__range=(start_date, end_date)
    ).select_related('product').order_by('-created_at')

    for event in events:
        writer.writerow([
            event.product.name,
            event.product.category,
            event.product.price,
            event.get_event_type_display(),
            event.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response
