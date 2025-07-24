from django.db import models
from accounts.models import Store
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
import string


# Create your models here.
class Product(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    image_url = models.URLField(max_length=1024, null=True, blank=True)
    page_url = models.URLField(max_length=1024, unique=True)  # URL به عنوان شناسه اصلی
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductEvent(models.Model):
    class EventType(models.TextChoices):
        VIEW = 'VIEW', 'بازدید محصول'
        ADD_TO_CART = 'ADD_TO_CART', 'افزودن به سبد'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_event_type_display()} for {self.product.name}"


class Recommendation(models.Model):
    class ReasonType(models.TextChoices):
        LOW_VIEW = 'LOW_VIEW', 'بازدید کم'
        HIGH_VIEW_LOW_ADD = 'HIGH_VIEW_LOW_ADD', 'بازدید بالا، افزودن به سبد کم'
        POPULAR_ITEM = 'POPULAR_ITEM', 'محصول محبوب'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='core_recommendations', null=True)
    reason = models.CharField(max_length=30, choices=ReasonType.choices)
    text = models.TextField(verbose_name="متن پیشنهاد")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"پیشنهاد برای {self.product.name}"


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Core_OTPCode')  # اصلاح شد
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (timezone.now() - self.created_at).total_seconds() < 120


class ApiKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='core_ApiKe')  # اصلاح شد
    key = models.CharField(max_length=40, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            alphabet = string.ascii_letters + string.digits
            self.key = 'sk_' + ''.join(secrets.choice(alphabet) for i in range(32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"API Key for {self.user.username}"
