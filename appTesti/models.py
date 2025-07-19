import uuid

from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from pip._vendor.rich.markup import Tag


# Create your models here.

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    full_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Website(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='websites',
                              verbose_name="صاحب سایت (مشتری)")
    name = models.CharField(max_length=100, verbose_name="نام نمایشی سایت")
    url = models.URLField(unique=True, verbose_name="آدرس سایت")
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="کلید API")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.url})"


class Category(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    source_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        unique_together = ('website', 'source_id')

    def __str__(self):
        return self.name


class Product(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='products')
    source_id = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    tags = models.JSONField(null=True, blank=True)
    attributes = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('website', 'source_id')

    def __str__(self):
        return self.name
