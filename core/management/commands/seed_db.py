import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

# مطمئن شوید که مسیر ایمپورت مدل‌ها صحیح است
from core.models import Product, ProductEvent, Recommendation


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های فیک برای تست تحلیلگر پر می‌کند.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('شروع فرآیند ساخت داده‌های تستی...'))

        # یک کاربر تستی برای مالکیت داده‌ها ایجاد یا دریافت کنید
        user, _ = User.objects.get_or_create(username='09120000000', defaults={'email': 'test@example.com'})

        # پاک کردن داده‌های قدیمی این کاربر برای جلوگیری از تکرار
        Product.objects.filter(owner=user).delete()
        Recommendation.objects.filter(owner=user).delete()

        faker = Faker('fa_IR')

        products_to_create = [
            {'name': 'گوشی هوشمند پرچمدار X20', 'base_views': 500},
            {'name': 'لپتاپ گیمینگ سری Alpha', 'base_views': 350},
            {'name': 'ساعت هوشمند FitLife 5', 'base_views': 800},
            {'name': 'هدفون بی‌سیم نویز کنسلینگ', 'base_views': 120},  # بازدید بالا، سبد خرید کم
            {'name': 'قهوه‌ساز اتوماتیک باریستا', 'base_views': 20},  # بازدید کم
            {'name': 'کنسول بازی نسل جدید Z-Box', 'base_views': 950},  # محصول محبوب
        ]

        products = []
        for i, p_data in enumerate(products_to_create):
            product = Product.objects.create(
                owner=user,
                name=p_data['name'],
                price=Decimal(random.randint(5, 500)) * 100000,
                page_url=f'https://test-shop.com/product/{i + 1}'
            )
            products.append((product, p_data['base_views']))

        self.stdout.write(self.style.SUCCESS(f'{len(products)} محصول فیک ایجاد شد.'))

        # --- ایجاد رویدادهای فیک (بازدید و افزودن به سبد) ---
        for product, base_views in products:
            # ایجاد بازدیدها
            for _ in range(random.randint(base_views - 50, base_views + 50)):
                ProductEvent.objects.create(
                    product=product,
                    event_type=ProductEvent.EventType.VIEW,
                    created_at=faker.date_time_between(start_date='-30d', end_date='now',
                                                       tzinfo=timezone.get_current_timezone())
                )

            # ایجاد رویدادهای افزودن به سبد (با یک نرخ تبدیل تصادفی)
            # برای محصول "هدفون بی‌سیم"، نرخ تبدیل را عمداً پایین نگه می‌داریم
            if 'هدفون' in product.name:
                conversion_rate = 0.01  # فقط ۱ درصد
            else:
                conversion_rate = random.uniform(0.05, 0.20)  # بین ۵ تا ۲۰ درصد

            view_count = ProductEvent.objects.filter(product=product, event_type=ProductEvent.EventType.VIEW).count()
            add_to_cart_count = int(view_count * conversion_rate)

            for _ in range(add_to_cart_count):
                ProductEvent.objects.create(
                    product=product,
                    event_type=ProductEvent.EventType.ADD_TO_CART,
                    created_at=faker.date_time_between(start_date='-30d', end_date='now',
                                                       tzinfo=timezone.get_current_timezone())
                )

        self.stdout.write(self.style.SUCCESS('رویدادهای بازدید و سبد خرید ایجاد شدند.'))

        # --- ایجاد پیشنهادهای هوشمند فیک بر اساس داده‌های ساخته شده ---

        # ۱. پیشنهاد برای محصول با بازدید کم
        low_view_product = Product.objects.get(name__contains='قهوه‌ساز')
        Recommendation.objects.create(
            owner=user,
            product=low_view_product,
            reason=Recommendation.ReasonType.LOW_VIEW,
            text='این محصول بازدید بسیار کمی دارد. آن را در صفحه اصلی یا در کمپین‌های تبلیغاتی خود معرفی کنید.'
        )

        # ۲. پیشنهاد برای محصول با بازدید بالا و سبد خرید کم
        attention_product = Product.objects.get(name__contains='هدفون')
        Recommendation.objects.create(
            owner=user,
            product=attention_product,
            reason=Recommendation.ReasonType.HIGH_VIEW_LOW_ADD,
            text='کاربران زیادی از این محصول بازدید می‌کنند اما آن را به سبد خرید اضافه نمی‌کنند. قیمت، توضیحات و تصاویر محصول را بازبینی کنید.'
        )

        # ۳. پیشنهاد برای محصول محبوب
        popular_product = Product.objects.get(name__contains='کنسول بازی')
        Recommendation.objects.create(
            owner=user,
            product=popular_product,
            reason=Recommendation.ReasonType.POPULAR_ITEM,
            text='این محصول ستاره فروشگاه شماست! موجودی انبار آن را همیشه چک کنید و در کنار آن محصولات مکمل مانند بازی یا دسته اضافه پیشنهاد دهید.'
        )

        self.stdout.write(self.style.SUCCESS('پیشنهادهای هوشمند فیک ایجاد شدند.'))
        self.stdout.write(self.style.SUCCESS('عملیات با موفقیت به پایان رسید!'))
