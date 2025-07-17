from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.conf import settings 


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=11)
    full_name = models.CharField(max_length=100 , blank=True)

    def __str__(self):
        return self.user.username


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (timezone.now() - self.created_at).total_seconds() < 120


class Category(models.Model):
    name = models.CharField(max_length=100)
    source_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.FloatField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    source_id = models.CharField(max_length=255, unique=True, null=True, blank=True)


    def __str__(self):
        return self.name


class UserEvent(models.Model):
    class EventType(models.TextChoices):
        PRODUCT_VIEW = 'VIEW', 'مشاهده محصول'
        ADD_TO_CART = 'CART', 'افزودن به سبد خرید'
        PURCHASE = 'BUY', 'خرید'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100, choices=EventType.choices)
    extra_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.event_type}"