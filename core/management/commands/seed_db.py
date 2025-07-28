# core/management/commands/populate_db.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, datetime
from core.models import Product, ProductEvent, Recommendation, Category


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های فیک و واقعی برای تست کامل داشبورد پر می‌کند.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🚀 شروع تولید داده‌های تستی برای داشبورد...'))

        faker = Faker('fa_IR')

        # --- ۱) آماده‌سازی ---
        user, _ = User.objects.get_or_create(username='09120000000', defaults={'email': 'testuser@example.com'})
        self.stdout.write(self.style.WARNING(f'🎯 داده‌ها برای کاربر "{user.username}" ساخته می‌شوند.'))

        ProductEvent.objects.filter(product__owner=user).delete()
        Recommendation.objects.filter(owner=user).delete()
        Product.objects.filter(owner=user).delete()
        Category.objects.filter(owner=user).delete()

        # --- ۲) دسته‌بندی‌ها ---
        categories = {}
        for name in ['کالای دیجیتال', 'لوازم خانگی', 'مد و پوشاک', 'ورزش و سفر', 'کتاب و لوازم تحریر']:
            categories[name] = Category.objects.create(owner=user, name=name)

        # --- ۳) محصولات با سناریو ---
        product_scenarios = [
            {'name': 'گوشی هوشمند پرچمدار P50 Pro', 'views': 950, 'conv': 0.15, 'buy': 0.7, 'stock': 50, 'category': 'کالای دیجیتال'},
            {'name': 'لپتاپ گیمینگ Legion X', 'views': 700, 'conv': 0.12, 'buy': 0.6, 'stock': 20, 'category': 'کالای دیجیتال'},
            {'name': 'کفش ورزشی نایکی ایرمکس', 'views': 1200, 'conv': 0.02, 'buy': 0.5, 'stock': 100, 'category': 'مد و پوشاک'},
            {'name': 'ساعت هوشمند گلکسی واچ ۶', 'views': 800, 'conv': 0.18, 'buy': 0.8, 'stock': 8, 'category': 'کالای دیجیتال'},
            {'name': 'قهوه‌ساز دلونگی', 'views': 250, 'conv': 0.08, 'buy': 0.4, 'stock': 30, 'category': 'لوازم خانگی'},
            {'name': 'کتاب فلسفه هنر', 'views': 80, 'conv': 0.05, 'buy': 0.9, 'stock': 50, 'category': 'کتاب و لوازم تحریر'},
        ]

        products = []
        for i, p in enumerate(product_scenarios):
            prod = Product.objects.create(
                owner=user,
                name=p['name'],
                price=Decimal(random.randint(3, 20)) * 1_000_000,
                stock=p['stock'],
                page_url=f'https://shop.com/product/{faker.slug()}-{i}',
                image_url=f'https://picsum.photos/seed/{i}/400/300',
                category=categories[p['category']]
            )
            products.append({'product': prod, 'scenario': p})

        # --- ۴) رویدادها ---
        self.stdout.write('📊 در حال ساخت رویدادهای بازدید، سبد خرید، خرید و تحلیل‌های ویژه...')
        today = timezone.now().date()
        loyal_users = ['192.168.1.100', '192.168.1.101']  # کاربران وفادار (آی‌پی ثابت)
        high_value_users = ['10.0.0.200']  # کاربران پرارزش (خرید زیاد)

        for item in products:
            product = item['product']
            s = item['scenario']

            # بازدید
            for _ in range(random.randint(s['views'] - 50, s['views'] + 50)):
                ip = random.choice(loyal_users + high_value_users + [faker.ipv4()])
                ProductEvent.objects.create(
                    product=product, event_type=ProductEvent.EventType.VIEW,
                    created_at=faker.date_time_between('-60d', 'now', tzinfo=timezone.get_current_timezone()),
                    user_ip=ip
                )

            # افزودن به سبد
            add_count = int(s['views'] * s['conv'])
            for _ in range(add_count):
                ProductEvent.objects.create(
                    product=product, event_type=ProductEvent.EventType.ADD_TO_CART,
                    created_at=faker.date_time_between('-30d', 'now', tzinfo=timezone.get_current_timezone()),
                    user_ip=faker.ipv4()
                )

            # خرید
            buy_count = int(add_count * s['buy'])
            for _ in range(buy_count):
                ip = random.choice(high_value_users + [faker.ipv4()])
                ProductEvent.objects.create(
                    product=product, event_type=ProductEvent.EventType.PURCHASE,
                    created_at=faker.date_time_between('-30d', 'now', tzinfo=timezone.get_current_timezone()),
                    user_ip=ip
                )

        # --- ۵) پیش‌بینی فروش: ساخت خریدهای یکنواخت در ۳۰ روز اخیر ---
        for days_ago in range(30):
            date_of_purchase = today - timedelta(days=days_ago)
            for _ in range(random.randint(1, 3)):
                prod = random.choice(products)['product']
                ProductEvent.objects.create(
                    product=prod, event_type=ProductEvent.EventType.PURCHASE,
                    created_at=timezone.make_aware(datetime.combine(date_of_purchase, datetime.min.time())),
                    user_ip=faker.ipv4()
                )

        # --- ۶) تحلیل سبد خرید: خرید هم‌زمان دو محصول ---
        for _ in range(20):
            pair = random.sample(products, 2)
            timestamp = faker.date_time_between('-15d', 'now', tzinfo=timezone.get_current_timezone())
            for p in pair:
                ProductEvent.objects.create(
                    product=p['product'], event_type=ProductEvent.EventType.PURCHASE,
                    created_at=timestamp,
                    user_ip=faker.ipv4()
                )

        # --- ۷) پیشنهادهای هوشمند ---
        attention = Product.objects.get(name__contains='کفش')
        Recommendation.objects.create(
            owner=user, product=attention, reason='HIGH_VIEW_LOW_ADD',
            text='بازدید زیاد ولی سبد خرید کم؛ شاید قیمت یا سایز دلیل باشد.',
            confidence_score=0.85, is_active=True
        )

        low_stock = Product.objects.get(name__contains='ساعت')
        Recommendation.objects.create(
            owner=user, product=low_stock, reason='LOW_STOCK',
            text='موجودی ساعت کمتر از ۱۰ عدد؛ شارژ فوری برای جلوگیری از اتمام موجودی.',
            confidence_score=0.98, is_active=True
        )

        self.stdout.write(self.style.SUCCESS('✅ همه داده‌ها ساخته شد! حالا داشبوردت پر و آماده است 🔥'))

