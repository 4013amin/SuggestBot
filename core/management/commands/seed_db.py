# core/management/commands/populate_db.py

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from core.models import Product, ProductEvent, Recommendation, Category


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های فیک و سناریوهای واقعی برای تست داشبورد پر می‌کند.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('شروع فرآیند ساخت داده‌های تستی...'))

        faker = Faker('fa_IR')

        # 1. --- ایجاد کاربر و پاک کردن داده‌های قدیمی ---
        user, _ = User.objects.get_or_create(username='09120000000', defaults={'email': 'testuser@example.com'})
        self.stdout.write(self.style.WARNING(f'داده‌ها برای کاربر "{user.username}" ایجاد خواهند شد.'))

        self.stdout.write(self.style.WARNING('در حال پاک کردن داده‌های قدیمی...'))
        ProductEvent.objects.filter(product__owner=user).delete()
        Recommendation.objects.filter(owner=user).delete()
        Product.objects.filter(owner=user).delete()
        Category.objects.filter(owner=user).delete()

        # 2. --- ایجاد دسته‌بندی‌ها ---
        categories = []
        category_names = ['کالای دیجیتال', 'لوازم خانگی', 'مد و پوشاک', 'ورزش و سفر', 'کتاب و لوازم تحریر']
        for name in category_names:
            category = Category.objects.create(owner=user, name=name)
            categories.append(category)
        self.stdout.write(self.style.SUCCESS(f'{len(categories)} دسته‌بندی ایجاد شد.'))

        # 3. --- تعریف سناریوهای محصولات ---
        # این سناریوها برای تست بخش‌های مختلف داشبورد طراحی شده‌اند
        product_scenarios = [
            {'name': 'گوشی هوشمند پرچمدار P50 Pro', 'base_views': 950, 'conversion_rate': 0.15, 'purchase_rate': 0.7,
             'stock': 50, 'category': 'کالای دیجیتال'},
            {'name': 'لپتاپ گیمینگ Legion X', 'base_views': 700, 'conversion_rate': 0.12, 'purchase_rate': 0.6,
             'stock': 20, 'category': 'کالای دیجیتال'},
            {'name': 'کفش ورزشی نایکی ایرمکس', 'base_views': 1200, 'conversion_rate': 0.02, 'purchase_rate': 0.5,
             'stock': 100, 'category': 'مد و پوشاک'},  # بازدید بالا، تبدیل کم
            {'name': 'ساعت هوشمند گلکسی واچ ۶', 'base_views': 800, 'conversion_rate': 0.18, 'purchase_rate': 0.8,
             'stock': 8, 'category': 'کالای دیجیتال'},  # موجودی کم
            {'name': 'قهوه‌ساز اتوماتیک دلونگی', 'base_views': 250, 'conversion_rate': 0.08, 'purchase_rate': 0.4,
             'stock': 30, 'category': 'لوازم خانگی'},
            {'name': 'کتاب فلسفه هنر', 'base_views': 80, 'conversion_rate': 0.05, 'purchase_rate': 0.9, 'stock': 50,
             'category': 'کتاب و لوازم تحریر'},  # بازدید کم
        ]

        created_products = []
        for i, p_data in enumerate(product_scenarios):
            category_obj = Category.objects.get(name=p_data['category'])
            product = Product.objects.create(
                owner=user,
                name=p_data['name'],
                price=Decimal(random.randint(1, 25)) * 1000000,
                stock=p_data['stock'],
                page_url=f'https://test-shop.com/product/{faker.slug()}-{i}',
                category=category_obj,
                image_url=f'https://picsum.photos/seed/{i}/400/300'
            )
            created_products.append({'product': product, 'scenario': p_data})

        self.stdout.write(self.style.SUCCESS(f'{len(created_products)} محصول با سناریوهای مشخص ایجاد شد.'))

        # 4. --- ایجاد رویدادهای فیک بر اساس سناریوها ---
        self.stdout.write('در حال ایجاد رویدادهای بازدید، سبد خرید و خرید...')
        for item in created_products:
            product = item['product']
            scenario = item['scenario']

            # ایجاد بازدیدها
            view_count = random.randint(scenario['base_views'] - 50, scenario['base_views'] + 50)
            for _ in range(view_count):
                ProductEvent.objects.create(
                    product=product,
                    event_type=ProductEvent.EventType.VIEW,
                    created_at=faker.date_time_between(start_date='-60d', end_date='now',
                                                       tzinfo=timezone.get_current_timezone()),
                    user_ip=faker.ipv4()
                )

            # ایجاد افزودن به سبد
            add_to_cart_count = int(view_count * scenario['conversion_rate'])
            for _ in range(add_to_cart_count):
                ProductEvent.objects.create(
                    product=product,
                    event_type=ProductEvent.EventType.ADD_TO_CART,
                    created_at=faker.date_time_between(start_date='-60d', end_date='now',
                                                       tzinfo=timezone.get_current_timezone()),
                    user_ip=faker.ipv4()
                )

            # ایجاد خریدها
            purchase_count = int(add_to_cart_count * scenario['purchase_rate'])
            for _ in range(purchase_count):
                ProductEvent.objects.create(
                    product=product,
                    event_type=ProductEvent.EventType.PURCHASE,
                    created_at=faker.date_time_between(start_date='-60d', end_date='now',
                                                       tzinfo=timezone.get_current_timezone()),
                    user_ip=faker.ipv4()
                )

        self.stdout.write(self.style.SUCCESS('رویدادها با موفقیت ایجاد شدند.'))

        # 5. --- ایجاد چند پیشنهاد هوشمند فیک برای تست ---
        try:
            attention_product = Product.objects.get(name__contains='کفش ورزشی')
            Recommendation.objects.create(
                owner=user, product=attention_product, reason='HIGH_VIEW_LOW_ADD',
                text='بازدیدکنندگان زیادی به این کفش علاقه‌مندند اما آن را نمی‌خرند. شاید قیمت بالا یا نبود سایز مناسب دلیل آن باشد.',
                confidence_score=0.85, is_active=True
            )

            low_stock_product = Product.objects.get(name__contains='ساعت هوشمند')
            Recommendation.objects.create(
                owner=user, product=low_stock_product, reason='LOW_STOCK',
                text=f'موجودی ساعت هوشمند به کمتر از ۱۰ عدد رسیده است. سریعا آن را شارژ کنید تا فروش را از دست ندهید.',
                confidence_score=0.98, is_active=True
            )
            self.stdout.write(self.style.SUCCESS('پیشنهادهای هوشمند فیک ایجاد شدند.'))
        except Product.DoesNotExist:
            self.stdout.write(self.style.WARNING('محصولات مورد نیاز برای ساخت پیشنهاد فیک یافت نشدند.'))

        self.stdout.write(self.style.SUCCESS('عملیات با موفقیت به پایان رسید! حالا می‌توانید داشبورد را بررسی کنید.'))