# core/management/commands/populate_db.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, datetime
from core.models import Product, Customer, ProductEvent, Recommendation  # مدل Customer اضافه شد


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های فیک و واقعی برای تست کامل داشبورد پر می‌کند.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🚀 شروع تولید داده‌های تستی برای داشبورد...'))

        faker = Faker('fa_IR')

        # --- ۱) آماده‌سازی ---
        # کاربر تستی که با آن وارد سیستم می‌شوید
        user, _ = User.objects.get_or_create(username='09120000000', defaults={'email': 'testuser@example.com'})
        self.stdout.write(self.style.WARNING(f'🎯 داده‌ها برای کاربر "{user.username}" ساخته می‌شوند.'))

        # پاک کردن داده‌های قبلی برای این کاربر
        ProductEvent.objects.filter(product__owner=user).delete()
        Recommendation.objects.filter(owner=user).delete()
        Product.objects.filter(owner=user).delete()
        Customer.objects.filter(owner=user).delete()  # مدل جدید مشتریان هم پاک می‌شود

        # --- ۲) محصولات با سناریو ---
        # دیگر به مدل Category نیازی نیست چون در مدل Product به CharField تبدیل شده
        product_scenarios = [
            {'name': 'گوشی هوشمند پرچمدار P50 Pro', 'views': 950, 'conv': 0.15, 'buy': 0.7, 'stock': 50,
             'category': 'کالای دیجیتال', 'price': 35_000_000},
            {'name': 'لپتاپ گیمینگ Legion X', 'views': 700, 'conv': 0.12, 'buy': 0.6, 'stock': 20,
             'category': 'کالای دیجیتال', 'price': 55_000_000},
            {'name': 'کفش ورزشی نایکی ایرمکس', 'views': 1200, 'conv': 0.02, 'buy': 0.5, 'stock': 100,
             'category': 'مد و پوشاک', 'price': 4_500_000},
            {'name': 'ساعت هوشمند گلکسی واچ ۶', 'views': 800, 'conv': 0.18, 'buy': 0.8, 'stock': 8,
             'category': 'کالای دیجیتال', 'price': 9_800_000},
            {'name': 'قهوه‌ساز دلونگی', 'views': 250, 'conv': 0.08, 'buy': 0.4, 'stock': 30, 'category': 'لوازم خانگی',
             'price': 7_200_000},
            {'name': 'کتاب فلسفه هنر', 'views': 80, 'conv': 0.05, 'buy': 0.9, 'stock': 50,
             'category': 'کتاب و لوازم تحریر', 'price': 250_000},
        ]

        products = []
        for i, p in enumerate(product_scenarios):
            prod = Product.objects.create(
                owner=user,
                product_id_from_site=f'prod-{i + 100}',
                name=p['name'],
                price=Decimal(p['price']),
                stock=p['stock'],
                page_url=f'https://shop.com/product/{faker.slug()}-{i}',
                category=p['category']  # <<<<==== تغییر کلیدی ۱: استفاده از متن ساده به جای آبجکت
            )
            products.append({'product': prod, 'scenario': p})

        # --- ۳) رویدادها ---
        self.stdout.write('📊 در حال ساخت رویدادها...')
        today = timezone.now().date()

        # شناسه‌های مشتریان برای سناریوهای مختلف
        loyal_customers_ids = ['customer-loyal-1', 'customer-loyal-2']
        high_value_customer_ids = ['customer-vip-1']
        all_special_ids = loyal_customers_ids + high_value_customer_ids

        for item in products:
            product = item['product']
            s = item['scenario']

            # ایجاد رویدادها با استفاده از مدل Customer
            for _ in range(s['views']):
                # انتخاب یک شناسه مشتری به صورت تصادفی
                customer_id = random.choice(all_special_ids + [f'random-user-{random.randint(1, 1000)}'])
                # <<<<==== تغییر کلیدی ۲: ساخت یا گرفتن مشتری به جای IP
                customer, _ = Customer.objects.get_or_create(owner=user, identifier=customer_id)
                ProductEvent.objects.create(
                    product=product,
                    customer=customer,  # اختصاص آبجکت مشتری
                    event_type=ProductEvent.EventType.VIEW,
                    created_at=faker.date_time_between('-60d', 'now', tzinfo=timezone.get_current_timezone()),
                )

            add_count = int(s['views'] * s['conv'])
            for _ in range(add_count):
                customer, _ = Customer.objects.get_or_create(owner=user,
                                                             identifier=f'random-user-{random.randint(1, 1000)}')
                ProductEvent.objects.create(product=product, customer=customer,
                                            event_type=ProductEvent.EventType.ADD_TO_CART)

            buy_count = int(add_count * s['buy'])
            for _ in range(buy_count):
                customer_id = random.choice(high_value_customer_ids + [f'random-user-{random.randint(1, 1000)}'])
                customer, _ = Customer.objects.get_or_create(owner=user, identifier=customer_id)
                ProductEvent.objects.create(product=product, customer=customer,
                                            event_type=ProductEvent.EventType.PURCHASE)

        # --- ۴) پیش‌بینی فروش ---
        top_product = Product.objects.get(name__contains='لپتاپ')
        for days_ago in range(60):
            date_of_purchase = today - timedelta(days=days_ago)
            for _ in range(random.randint(0, 5)):
                customer, _ = Customer.objects.get_or_create(owner=user,
                                                             identifier=f'random-user-{random.randint(1, 1000)}')
                ProductEvent.objects.create(
                    product=top_product, customer=customer, event_type=ProductEvent.EventType.PURCHASE,
                    created_at=timezone.make_aware(datetime.combine(date_of_purchase, datetime.min.time()))
                )

        # --- ۵) تحلیل سبد خرید ---
        pair_to_buy = [Product.objects.get(name__contains='گوشی'), Product.objects.get(name__contains='ساعت')]
        for _ in range(25):
            customer_id = f'basket-user-{random.randint(1, 50)}'
            customer, _ = Customer.objects.get_or_create(owner=user, identifier=customer_id)
            timestamp = faker.date_time_between('-15d', 'now', tzinfo=timezone.get_current_timezone())
            ProductEvent.objects.create(product=pair_to_buy[0], customer=customer,
                                        event_type=ProductEvent.EventType.PURCHASE, created_at=timestamp)
            ProductEvent.objects.create(product=pair_to_buy[1], customer=customer,
                                        event_type=ProductEvent.EventType.PURCHASE, created_at=timestamp)

        # --- ۶) پیشنهادهای هوشمند ---
        attention_product = Product.objects.get(name__contains='کفش')
        Recommendation.objects.create(owner=user, product=attention_product, reason='HIGH_VIEW_LOW_ADD',
                                      text='کفش ورزشی نایکی بازدید زیادی دارد اما به سبد خرید اضافه نمی‌شود. قیمت‌گذاری یا تصاویر محصول را بررسی کنید.',
                                      confidence_score=0.85)

        low_stock_product = Product.objects.get(name__contains='ساعت')
        Recommendation.objects.create(owner=user, product=low_stock_product, reason='LOW_STOCK',
                                      text='موجودی ساعت هوشمند رو به اتمام است. برای جلوگیری از توقف فروش، سریعاً آن را شارژ کنید.',
                                      confidence_score=0.98)

        self.stdout.write(self.style.SUCCESS('✅ همه داده‌ها با موفقیت ساخته شد! داشبورد شما اکنون آماده نمایش است 🔥'))
