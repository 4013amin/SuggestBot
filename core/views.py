import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q
from .forms import OTPRequestForm, OTPVerifyForm
from .models import OTPCode, ApiKey, Product, ProductEvent, Recommendation


# ==============================================================================
# >> بخش تحلیل و تولید پیشنهادها (نسخه نهایی و ضد خطا) <<
# ==============================================================================

def update_recommendations(user):
    """
    این تابع به صورت امن پیشنهادها را تولید و مدیریت می‌کند تا از ایجاد
    رکورد تکراری و بروز خطای MultipleObjectsReturned جلوگیری شود.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # --- تحلیل تک تک محصولات ---
    products = Product.objects.filter(owner=user)
    for product in products:
        events = product.events.filter(created_at__gte=thirty_days_ago)
        views = events.filter(event_type='VIEW').count()
        add_to_carts = events.filter(event_type='ADD_TO_CART').count()
        conversion_rate = (add_to_carts / views * 100) if views > 0 else 0

        current_reason, current_text = None, None

        if views > 50 and conversion_rate > 5:
            current_reason, current_text = 'POPULAR_ITEM', f"دمت گرم! محصول '{product.name}' حسابی محبوبه. روی تبلیغاتش بیشتر کار کن."
        elif views > 30 and conversion_rate < 1:
            current_reason, current_text = 'HIGH_VIEW_LOW_ADD', f"رفیق، خیلیا میان سراغ '{product.name}' ولی نمی‌خرن. قیمت، عکس‌ها و توضیحاتش رو یه بازبینی کن."
        elif views < 10 and product.created_at < timezone.now() - timedelta(days=7):
            current_reason, current_text = 'LOW_VIEW', f"انگار محصول '{product.name}' خوب دیده نشده. توی صفحه اصلی یا شبکه‌های اجتماعی معرفیش کن."

        if current_reason and current_text:
            # ۱. ابتدا پیشنهاد درست را ایجاد یا آپدیت می‌کنیم و مطمئن می‌شویم فعال است.
            rec_obj, created = Recommendation.objects.update_or_create(
                owner=user,
                product=product,
                reason=current_reason,
                defaults={'text': current_text, 'is_active': True}
            )
            # ۲. سپس، تمام پیشنهادهای *دیگر* برای این محصول را غیرفعال می‌کنیم.
            product.core_recommendations.exclude(pk=rec_obj.pk).update(is_active=False)
        else:
            # اگر محصول دیگر شرایط هیچ پیشنهادی را ندارد، همه را غیرفعال کن.
            product.core_recommendations.update(is_active=False)

    # --- تحلیل کلی سایت ---
    all_events = ProductEvent.objects.filter(product__owner=user, created_at__gte=thirty_days_ago)
    total_views = all_events.filter(event_type='VIEW').count()
    total_carts = all_events.filter(event_type='ADD_TO_CART').count()
    overall_conversion = (total_carts / total_views * 100) if total_views > 0 else 0

    general_reason, general_text = None, None
    if total_views > 100 and overall_conversion < 1:
        general_reason, general_text = 'HIGH_VIEW_LOW_ADD', "بازدید کلی سایتت خوبه اما نرخ تبدیل پایینه! شاید بهتر باشه فرایند پرداخت یا هزینه‌های ارسال رو بازبینی کنی."
    elif total_views < 50 and products.exists():
        general_reason, general_text = 'LOW_VIEW', "بازدید کلی سایت کمه. روی سئو و تبلیغات عمومی بیشتر کار کن تا مشتری‌های جدید پیدات کنن."

    if general_reason and general_text:
        rec_obj, created = Recommendation.objects.update_or_create(
            owner=user,
            product__isnull=True,
            reason=general_reason,
            defaults={'text': general_text, 'is_active': True}
        )
        Recommendation.objects.filter(owner=user, product__isnull=True).exclude(pk=rec_obj.pk).update(is_active=False)
    else:
        Recommendation.objects.filter(owner=user, product__isnull=True).update(is_active=False)


# ==============================================================================
# >> بقیه ویوها بدون تغییر باقی می‌مانند <<
# ==============================================================================

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

    if not request.GET.get('start_date'):
        update_recommendations(user)

    products = Product.objects.filter(owner=user)
    all_events = ProductEvent.objects.filter(product__in=products, created_at__range=(start_date, end_date))
    total_views = all_events.filter(event_type='VIEW').count()
    total_add_to_cart = all_events.filter(event_type='ADD_TO_CART').count()

    date_filter = Q(events__created_at__range=(start_date, end_date))
    views_in_range = Count('events', filter=Q(events__event_type='VIEW') & date_filter)
    carts_in_range = Count('events', filter=Q(events__event_type='ADD_TO_CART') & date_filter)

    popular_products = products.annotate(
        views_count=views_in_range,
        carts_count=carts_in_range
    ).order_by('-carts_count', '-views_count')[:5]

    attention_products = products.annotate(
        views_count=views_in_range,
        carts_count=carts_in_range
    ).filter(views_count__gt=20, carts_count=0).order_by('-views_count')[:5]

    latest_recommendations = Recommendation.objects.filter(owner=user, is_active=True).order_by('-created_at')[:5]

    context = {
        'total_views': total_views, 'total_add_to_cart': total_add_to_cart, 'product_count': products.count(),
        'popular_products': popular_products, 'attention_products': attention_products,
        'recommendations': latest_recommendations, 'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'), 'is_custom_date_range': 'start_date' in request.GET,
    }
    return render(request, 'dashboard_overview.html', context)


# (توابع دیگر مانند request_otp_view, product_detail_view و غیره را در اینجا قرار دهید...)
# ... (کدهای دیگر ویوها که بدون تغییر هستند)
def request_otp_view(request):
    if request.user.is_authenticated:
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
            return redirect('core:verify_otp')
    else:
        form = OTPRequestForm()
    return render(request, 'request_otp.html', {'form': form})


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
                    return redirect('core:dashboard_overview')
                else:
                    form.add_error('code', 'کد منقضی شده است. لطفاً دوباره تلاش کنید.')
            except (OTPCode.DoesNotExist, User.DoesNotExist):
                form.add_error('code', 'کد وارد شده صحیح نیست.')
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
    conversion_rate = (carts_30_days / views_30_days * 100) if views_30_days > 0 else 0

    chart_labels, chart_views = [], []
    today = timezone.now()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = product.events.filter(event_type='VIEW', created_at__date=day.date()).count()
        chart_labels.append(day.strftime('%A'))
        chart_views.append(count)

    product_recommendations = product.core_recommendations.filter(is_active=True)

    context = {
        'product': product, 'views_30_days': views_30_days, 'carts_30_days': carts_30_days,
        'conversion_rate': f"{conversion_rate:.2f}", 'chart_labels': chart_labels, 'chart_views': chart_views,
        'recommendations': product_recommendations
    }
    return render(request, 'product_detail.html', context)