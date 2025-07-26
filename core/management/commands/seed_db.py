import random

import self
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from core.models import Product, ProductEvent, Recommendation


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های فیک برای تست تحلیلگر پر می‌کند.'

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.SUCCESS('شروع فرآیند ساخت داده‌های تستی...'))

    # یک کاربر تستی برای مالکیت داده‌ها
    user, _ = User.objects.get_or_create(username='09120000000', defaults={'email': 'test@example.com'})

    # پاک کردن داده‌های قدیمی این کاربر
    Product.objects.filter(owner=user).delete()
    Recommendation.objects.filter(owner=user).delete()

    faker = Faker('fa_IR')

    # تعریف محصولات با ویژگی‌های متنوع
    products_to_create = [
        {'name': 'گوشی هوشمند پرچمدار X20', 'base_views': 500, 'stock': 50, 'discount': 10},
        {'name': 'لپتاپ گیمینگ سری Alpha', 'base_views': 350, 'stock': 20, 'discount': 5},
        {'name': 'ساعت هوشمند FitLife 5', 'base_views': 800, 'stock': 10, 'discount': 15},
        {'name': 'هدفون بی‌سیم نویز کنسلینگ', 'base_views': 120, 'stock': 100, 'discount': 0},
        # بازدید بالا، سبد خرید کم
        {'name': 'قهوه‌ساز اتوماتیک باریستا', 'base_views': 20, 'stock': 5, 'discount': 30},  # بازدید و موجودی کم
        {'name': 'کنسول بازی نسل جدید Z-Box', 'base_views': 950, 'stock': 30, 'discount': 20},  # محصول محبوب
    ]

    products = []
    for i, p_data in enumerate(products_to_create):
        product = Product.objects.create(
            owner=user,
            name=p_data['name'],
            price=Decimal(random.randint(5, 500)) * 100000,
            stock=p_data['stock'],
            discount=p_data['discount'],
            page_url=f'https://test-shop.com/product/{i + 1}',
            category=faker.word(),
            image_url=f'https://test-shop.com/images/product_{i + 1}.jpg'
        )
    products.append((product, p_data['base_views']))
    self.stdout.write(
        self.style.SUCCESS(f'محصول "{product.name}" با موجودی {product.stock} و تخفیف {product.discount}% ایجاد شد.'))

    self.stdout.write(self.style.SUCCESS(f'{len(products)} محصول فیک ایجاد شد.'))

    # --- ایجاد رویدادهای فیک (بازدید، افزودن به سبد، خرید) ---
    for product, base_views in products:
        for _ in range(random.randint(base_views - 50, base_views + 50)):
            ProductEvent.objects.create(
                product=product,
                event_type=ProductEvent.EventType.VIEW,
                created_at=faker.date_time_between(start_date='-30d', end_date='now',
                                                   tzinfo=timezone.get_current_timezone())
            )

    # افزودن به سبد خرید
    if 'هدفون' in product.name:
        conversion_rate = 0.01  # نرخ تبدیل پایین
    else:
        conversion_rate = random.uniform(0.05, 0.20)

    view_count = ProductEvent.objects.filter(product=product, event_type=ProductEvent.EventType.VIEW).count()
    add_to_cart_count = int(view_count * conversion_rate)

    for _ in range(add_to_cart_count):
        ProductEvent.objects.create(
            product=product,
            event_type=ProductEvent.EventType.ADD_TO_CART,
            created_at=faker.date_time_between(start_date='-30d', end_date='now',
                                               tzinfo=timezone.get_current_timezone())
        )

    # خریدها (نرخ خرید بین 20% تا 80% از افزودن به سبد)
    purchase_rate = random.uniform(0.2, 0.8)
    purchase_count = int(add_to_cart_count * purchase_rate)
    for _ in range(purchase_count):
        ProductEvent.objects.create(
            product=product,
            event_type=ProductEvent.EventType.PURCHASE,
            created_at=faker.date_time_between(start_date='-30d', end_date='now',
                                               tzinfo=timezone.get_current_timezone())
        )

    self.stdout.write(self.style.SUCCESS('رویدادهای بازدید، سبد خرید و خرید ایجاد شدند.'))

    # --- ایجاد پیشنهادهای هوشمند فیک ---
    # ۱. پیشنهاد برای محصول با بازدید کم
    low_view_product = Product.objects.get(name__contains='قهوه‌ساز')
    Recommendation.objects.create(
        owner=user,
        product=low_view_product,
        reason='LOW_VIEW',
        text='این محصول بازدید بسیار کمی دارد. آن را در صفحه اصلی یا در کمپین‌های تبلیغاتی خود معرفی کنید.',
        confidence_score=0.7,
        is_active=True
    )

    # ۲. پیشنهاد برای محصول با بازدید بالا و سبد خرید کم
    attention_product = Product.objects.get(name__contains='هدفون')
    Recommendation.objects.create(
        owner=user,
        product=attention_product,
        reason='HIGH_VIEW_LOW_ADD',
        text='کاربران زیادی از این محصول بازدید می‌کنند اما آن را به سبد خرید اضافه نمی‌کنند. قیمت، توضیحات و تصاویر محصول را بازبینی کنید.',
        confidence_score=0.8,
        is_active=True
    )

    # ۳. پیشنهاد برای محصول محبوب
    popular_product = Product.objects.get(name__contains='کنسول بازی')
    Recommendation.objects.create(
        owner=user,
        product=popular_product,
        reason='POPULAR_ITEM',
        text='این محصول ستاره فروشگاه شماست! موجودی انبار آن را همیشه چک کنید و در کنار آن محصولات مکمل مانند بازی یا دسته اضافه پیشنهاد دهید.',
        confidence_score=0.9,
        is_active=True
    )

    # ۴. پیشنهاد قیمت‌گذاری پویا
    for product in Product.objects.filter(owner=user):
        view_count = product.events.filter(event_type='VIEW').count()
    cart_count = product.events.filter(event_type='ADD_TO_CART').count()
    conversion_rate = (cart_count / view_count * 100) if view_count > 0 else 0
    if view_count > 50 and conversion_rate < 2:
        suggestion = f"برای '{product.name}'، قیمت را به {float(product.price) * 0.9:.2f} کاهش دهید تا فروش افزایش یابد."
    Recommendation.objects.create(
        owner=user,
        product=product,
        reason='DYNAMIC_PRICING',
        text=suggestion,
        confidence_score=0.85,
        is_active=True
    )
    suggestion = f"تقاضا برای '{product.name}' بالاست. می‌توانید قیمت را به {float(product.price) * 1.1:.2f} افزایش دهید."
    Recommendation.objects.create(
        owner=user,
        product=product,
        reason='DYNAMIC_PRICING',
        text=suggestion,
        confidence_score=0.9,
        is_active=True
    )

    # ۵. پیشنهاد کلی سایت
    total_views = ProductEvent.objects.filter(product__owner=user, event_type='VIEW').count()
    total_carts = ProductEvent.objects.filter(product__owner=user, event_type='ADD_TO_CART').count()
    overall_conversion = (total_carts / total_views * 100) if total_views > 0 else 0
    if total_views > 100 and overall_conversion < 1:
        Recommendation.objects.create(
            owner=user,
            product=None,
            reason='HIGH_VIEW_LOW_ADD',
            text='بازدید کلی سایت بالا اما نرخ تبدیل پایین است. فرایند پرداخت یا هزینه‌های ارسال را بررسی کنید.',
            confidence_score=0.8,
            is_active=True
        )

    self.stdout.write(self.style.SUCCESS('پیشنهادهای هوشمند فیک و قیمت‌گذاری پویا ایجاد شدند.'))
    self.stdout.write(self.style.SUCCESS('عملیات با موفقیت به پایان رسید!'))
