# core/models.py

import secrets
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'

    def __str__(self):
        return self.name


class Customer(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers', null=True)
    identifier = models.CharField(max_length=255, help_text="شناسه مشتری (IP یا شناسه از سایت شما)", null=True)
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مشتری'
        verbose_name_plural = 'مشتریان'
        unique_together = ('owner', 'identifier')

    def __str__(self):
        return self.identifier


class Product(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    product_id_from_site = models.CharField(max_length=255, help_text="شناسه محصول در سایت شما", default='unknown')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    page_url = models.URLField(max_length=1024)
    stock = models.IntegerField(default=0, null=True, blank=True)
    category = models.CharField(max_length=255, default='عمومی')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        unique_together = ('owner', 'product_id_from_site')

    def __str__(self):
        return self.name


class ProductEvent(models.Model):
    class EventType(models.TextChoices):
        VIEW = 'VIEW', 'بازدید محصول'
        ADD_TO_CART = 'ADD_TO_CART', 'افزودن به سبد'
        PURCHASE = 'PURCHASE', 'خرید نهایی'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.VIEW)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'رویداد محصول'
        verbose_name_plural = 'رویدادهای محصولات'

    def __str__(self):
        return f"{self.get_event_type_display()} for {self.product.name if self.product else 'Unknown'} by {self.customer.identifier if self.customer else 'Unknown'}"


class Recommendation(models.Model):
    class ReasonType(models.TextChoices):
        LOW_VIEW = 'LOW_VIEW', 'بازدید کم'
        HIGH_VIEW_LOW_ADD = 'HIGH_VIEW_LOW_ADD', 'بازدید بالا، افزودن به سبد کم'
        POPULAR_ITEM = 'POPULAR_ITEM', 'محصول محبوب'
        LOW_STOCK = 'LOW_STOCK', 'موجودی کم'
        HIGH_DISCOUNT = 'HIGH_DISCOUNT', 'تخفیف بالا'
        AI_GENERATED = 'AI_GENERATED', 'پیشنهاد هوش مصنوعی'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='core_recommendations', null=True,
                                blank=True)
    reason = models.CharField(max_length=30, choices=ReasonType.choices)
    text = models.TextField(verbose_name="متن پیشنهاد")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confidence_score = models.FloatField(default=0.0)

    class Meta:
        verbose_name = 'پیشنهاد'
        verbose_name_plural = 'پیشنهادات'

    def __str__(self):
        return f"پیشنهاد برای {self.product.name if self.product else 'کل سایت'}"


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='core_otpcode')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (timezone.now() - self.created_at).total_seconds() < 120


class ApiKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='core_apikey')
    key = models.CharField(max_length=40, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            alphabet = string.ascii_letters + string.digits
            self.key = 'sk_' + ''.join(secrets.choice(alphabet) for _ in range(32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"API Key for {self.user.username}"


class UserSite(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sites')
    site_url = models.URLField(unique=True, verbose_name='آدرس سایت')
    api_key = models.OneToOneField(ApiKey, on_delete=models.CASCADE, related_name='site')
    is_active = models.BooleanField(default=True, verbose_name='وضعیت فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    def __str__(self):
        return self.site_url


class ABTest(models.Model):
    class TestVariable(models.TextChoices):
        PRICE = 'PRICE', 'قیمت'
        NAME = 'NAME', 'عنوان محصول'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ab_tests')
    name = models.CharField(max_length=255, verbose_name="نام تست")
    variable = models.CharField(max_length=20, choices=TestVariable.choices, verbose_name="متغیر مورد تست")
    control_value = models.CharField(max_length=255, help_text="مقدار اصلی یا کنترل")
    variant_value = models.CharField(max_length=255, help_text="مقدار جدید برای تست")
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'تست A/B'
        verbose_name_plural = 'تست‌های A/B'

    def __str__(self):
        return f"تست '{self.name}' برای محصول '{self.product.name}'"


class ABTestEvent(models.Model):
    class VariantType(models.TextChoices):
        CONTROL = 'CONTROL', 'کنترل'
        VARIANT = 'VARIANT', 'متغیر جدید'

    class EventType(models.TextChoices):
        VIEW = 'VIEW', 'نمایش'
        CONVERSION = 'CONVERSION', 'تبدیل (خرید)'

    test = models.ForeignKey(ABTest, on_delete=models.CASCADE, related_name='test_events')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='test_events')
    variant_shown = models.CharField(max_length=20, choices=VariantType.choices)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'رویداد تست A/B'
        verbose_name_plural = 'رویدادهای تست A/B'
