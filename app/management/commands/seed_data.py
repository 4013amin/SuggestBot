from django.core.management.base import BaseCommand
from django.db import transaction
from app.models import UserEvent, Product, Category
import random


class Command(BaseCommand):
    help = 'پایگاه داده را با داده‌های تستی برای محصولات و رویدادها پر می‌کند'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("شروع پاکسازی داده‌های قدیمی...")
        Product.objects.all().delete()
        Category.objects.all().delete()
        UserEvent.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("داده ها پاک شدن ..."))

        self.stdout.write("ایجاد دسته بندی ها و محصولات تستی...")
        cat1 = Category.objects.create(name="پوشاک مردانه", source_id="wc_cat_1")
        cat2 = Category.objects.create(name="کالای دیجیتال", source_id="wc_cat_2")

        p1 = Product.objects.create(name="تیشرت مردانه", price=150000, category=cat1, source_id="wp_101")
        p2 = Product.objects.create(name="تیشرت مردانه", price=150000, category=cat1, source_id="wp_102")
        p3 = Product.objects.create(name="تیشرت مردانه", price=150000, category=cat1, source_id="wp_103")
        p4 = Product.objects.create(name="تیشرت مردانه", price=150000, category=cat2, source_id="wp_104")
        p5 = Product.objects.create(name="تیشرت مردانه", price=150000, category=cat2, source_id="wp_105")

        products = [p1, p2, p3, p4, p5]
        self.stdout.write(self.style.SUCCESS(f"{len(products)} محصول ایجاد شد."))

        self.stdout.write("شبیه سازی رفتار کاربران")

        # کاربران ۱
        UserEvent.objects.create(session_id="session_user_1", event_type='VIEW', product=p1)
        UserEvent.objects.create(session_id="session_user_1", event_type='VIEW', product=p2)
        UserEvent.objects.create(session_id="session_user_1", event_type='VIEW', product=p3)

        # کاربران ۲
        UserEvent.objects.create(session_id="session_user_2", event_type='VIEW', product=p1)
        UserEvent.objects.create(session_id="session_user_2", event_type='VIEW', product=p2)
        UserEvent.objects.create(session_id="session_user_2", event_type='VIEW', product=p3)

        UserEvent.objects.create(session_id="session_user_3", event_type='VIEW', product=p4)
        UserEvent.objects.create(session_id="session_user_3", event_type='VIEW', product=p5)

        self.stdout.write("داده های فیک اضافه شدن")
