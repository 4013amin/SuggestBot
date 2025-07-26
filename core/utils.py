import requests
import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from .models import Product, ProductEvent, Recommendation

logger = logging.getLogger(__name__)

# تنظیمات API هوش مصنوعی (مثلاً xAI API)
AI_API_URL = "https://api.x.ai/v1/recommendations"  # آدرس API مدل هوش مصنوعی
AI_API_KEY = "your-ai-api-key"  # کلید API (باید از x.ai/api دریافت شود)


def fetch_data_for_analysis(user, start_date, end_date):
    """
    جمع‌آوری داده‌های کلی و جزئی برای تحلیل.
    """
    products = Product.objects.filter(owner=user)
    events = ProductEvent.objects.filter(
        product__in=products, created_at__range=(start_date, end_date)
    )

    # تحلیل جزئی برای هر محصول
    product_stats = []
    for product in products:
        product_events = events.filter(product=product)
        views = product_events.filter(event_type='VIEW').count()
        carts = product_events.filter(event_type='ADD_TO_CART').count()
        purchases = product_events.filter(event_type='PURCHASE').count()
        conversion_rate = (carts / views * 100) if views > 0 else 0
        purchase_rate = (purchases / views * 100) if views > 0 else 0

        product_stats.append({
            'product_id': product.id,
            'name': product.name,
            'views': views,
            'carts': carts,
            'purchases': purchases,
            'conversion_rate': conversion_rate,
            'purchase_rate': purchase_rate,
            'stock': product.stock,
            'price': float(product.price or 0),
            'discount': float(product.discount or 0),
            'category': product.category,
        })

    # تحلیل کلی سایت
    total_views = events.filter(event_type='VIEW').count()
    total_carts = events.filter(event_type='ADD_TO_CART').count()
    total_purchases = events.filter(event_type='PURCHASE').count()
    overall_conversion = (total_carts / total_views * 100) if total_views > 0 else 0
    overall_purchase_rate = (total_purchases / total_views * 100) if total_views > 0 else 0

    return {
        'products': product_stats,
        'site_stats': {
            'total_views': total_views,
            'total_carts': total_carts,
            'total_purchases': total_purchases,
            'overall_conversion': overall_conversion,
            'overall_purchase_rate': overall_purchase_rate,
        }
    }


def generate_ai_recommendations(user, data):
    """
    اتصال به مدل هوش مصنوعی برای تولید پیشنهادات پیشرفته.
    """
    try:
        headers = {
            'Authorization': f'Bearer {AI_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.post(AI_API_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        ai_recommendations = response.json().get('recommendations', [])

        for rec in ai_recommendations:
            product_id = rec.get('product_id')
            product = Product.objects.get(id=product_id) if product_id else None
            Recommendation.objects.update_or_create(
                owner=user,
                product=product,
                reason='AI_GENERATED',
                defaults={
                    'text': rec.get('text'),
                    'is_active': True,
                    'confidence_score': rec.get('confidence', 0.0)
                }
            )
        logger.info(f"AI recommendations generated for user: {user.username}")
    except requests.RequestException as e:
        logger.error(f"Error connecting to AI API: {str(e)}")


def update_recommendations(user, start_date, end_date, product=None):
    """
    تولید و به‌روزرسانی پیشنهادات بر اساس تحلیل داده‌ها و مدل هوش مصنوعی.
    """
    if product:
        # تحلیل برای یک محصول خاص
        product_data = fetch_product_data(product, start_date, end_date)
        views = product_data['views']
        carts = product_data['carts']
        purchases = product_data['purchases']
        conversion_rate = product_data['conversion_rate']
        stock = product_data['stock']
        discount = product_data['discount']

        current_reason, current_text = None, None
        if views > 50 and conversion_rate > 5:
            current_reason = 'POPULAR_ITEM'
            current_text = f"محصول '{product.name}' پرطرفداره! تبلیغاتش رو بیشتر کن."
        elif views > 30 and conversion_rate < 1:
            current_reason = 'HIGH_VIEW_LOW_ADD'
            current_text = f"محصول '{product.name}' بازدید زیادی داره ولی فروشش کمه. قیمت یا توضیحات رو چک کن."
        elif views < 10 and product.created_at < timezone.now() - timedelta(days=7):
            current_reason = 'LOW_VIEW'
            current_text = f"محصول '{product.name}' دیده نمی‌شه. توی شبکه‌های اجتماعی یا صفحه اصلی تبلیغش کن."
        elif stock < 5 and stock > 0:
            current_reason = 'LOW_STOCK'
            current_text = f"موجودی '{product.name}' کمه. زودتر شارژش کن."
        elif discount > 20:
            current_reason = 'HIGH_DISCOUNT'
            current_text = f"تخفیف '{product.name}' زیاده. سودآوری رو بررسی کن."

        if current_reason and current_text:
            rec_obj, created = Recommendation.objects.update_or_create(
                owner=user,
                product=product,
                reason=current_reason,
                defaults={'text': current_text, 'is_active': True}
            )
            product.core_recommendations.exclude(pk=rec_obj.pk).update(is_active=False)
        else:
            product.core_recommendations.update(is_active=False)

        # پیشنهادات هوش مصنوعی برای محصول خاص
        generate_ai_recommendations(user, product_data)
    else:
        # تحلیل کل سایت
        data = fetch_data_for_analysis(user, start_date, end_date)
        for product_data in data['products']:
            product = Product.objects.get(id=product_data['product_id'])
            views = product_data['views']
            carts = product_data['carts']
            purchases = product_data['purchases']
            conversion_rate = product_data['conversion_rate']
            stock = product_data['stock']
            discount = product_data['discount']

            current_reason, current_text = None, None
            if views > 50 and conversion_rate > 5:
                current_reason = 'POPULAR_ITEM'
                current_text = f"محصول '{product.name}' بسیار محبوب است. روی تبلیغات و بازاریابی آن تمرکز کنید."
            elif views > 30 and conversion_rate < 1:
                current_reason = 'HIGH_VIEW_LOW_ADD'
                current_text = f"محصول '{product.name}' بازدید زیادی دارد اما فروش کمی. قیمت، تصاویر یا توضیحات را بررسی کنید."
            elif views < 10 and product.created_at < timezone.now() - timedelta(days=7):
                current_reason = 'LOW_VIEW'
                current_text = f"محصول '{product.name}' بازدید کمی دارد. آن را در صفحه اصلی یا شبکه‌های اجتماعی تبلیغ کنید."
            elif stock < 5 and stock > 0:
                current_reason = 'LOW_STOCK'
                current_text = f"موجودی '{product.name}' کم است. سریعاً موجودی را شارژ کنید."
            elif discount > 20:
                current_reason = 'HIGH_DISCOUNT'
                current_text = f"تخفیف '{product.name}' بالاست. بررسی کنید که آیا سودآوری حفظ شده است."

            if current_reason and current_text:
                rec_obj, created = Recommendation.objects.update_or_create(
                    owner=user,
                    product=product,
                    reason=current_reason,
                    defaults={'text': current_text, 'is_active': True}
                )
                product.core_recommendations.exclude(pk=rec_obj.pk).update(is_active=False)
            else:
                product.core_recommendations.update(is_active=False)

        # تحلیل کلی سایت
        site_stats = data['site_stats']
        total_views = site_stats['total_views']
        overall_conversion = site_stats['overall_conversion']

        general_reason, general_text = None, None
        if total_views > 100 and overall_conversion < 1:
            general_reason = 'HIGH_VIEW_LOW_ADD'
            general_text = "بازدید کلی سایت بالا اما نرخ تبدیل پایین است. فرایند پرداخت یا هزینه‌های ارسال را بررسی کنید."
        elif total_views < 50 and Product.objects.filter(owner=user).exists():
            general_reason = 'LOW_VIEW'
            general_text = "بازدید کلی سایت کم است. روی سئو و تبلیغات عمومی بیشتر کار کنید."

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

        # پیشنهادات هوش مصنوعی برای کل سایت
        generate_ai_recommendations(user, data)

def fetch_product_data(product, start_date, end_date):
    """جمع‌آوری داده‌های خاص یک محصول برای تحلیل"""
    events = product.events.filter(created_at__range=(start_date, end_date))
    views = events.filter(event_type='VIEW').count()
    carts = events.filter(event_type='ADD_TO_CART').count()
    purchases = events.filter(event_type='PURCHASE').count()
    conversion_rate = (carts / views * 100) if views > 0 else 0
    purchase_rate = (purchases / views * 100) if views > 0 else 0

    return {
        'product_id': product.id,
        'name': product.name,
        'views': views,
        'carts': carts,
        'purchases': purchases,
        'conversion_rate': conversion_rate,
        'purchase_rate': purchase_rate,
        'stock': product.stock,
        'price': float(product.price or 0),
        'discount': float(product.discount or 0),
        'category': product.category,
    }


def predict_cart_abandonment(user, product, start_date, end_date):
    product_data = fetch_product_data(product, start_date, end_date)
    try:
        headers = {
            'Authorization': f'Bearer {AI_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'product_id': product_data['product_id'],
            'views': product_data['views'],
            'carts': product_data['carts'],
            'purchases': product_data['purchases'],
            'conversion_rate': product_data['conversion_rate']
        }
        response = requests.post(f"{AI_API_URL}/recommendations", json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        abandonment_score = result.get('abandonment_score', 0.0)
        suggestion = result.get('suggestion', 'هیچ پیشنهادی در دسترس نیست.')
        return abandonment_score, suggestion
    except requests.RequestException as e:
        logger.error(f"Error predicting cart abandonment: {str(e)}")
        return 0.0, "خطا در دریافت پیش‌بینی"