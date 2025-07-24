from django.contrib.auth.models import User
from django.db import models


# Create your models here.
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام محصول")
    product_id_woocommerce = models.IntegerField(unique=True, verbose_name="شناسه محصول در ووکامرس")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت")
    stock_quantity = models.IntegerField(default=0, verbose_name="موجودی انبار")

    def __str__(self):
        return self.name

class Order(models.Model):
    order_id_woocommerce = models.IntegerField(unique=True, verbose_name="شناسه سفارش در ووکامرس")
    customer_name = models.CharField(max_length=255, verbose_name="نام مشتری")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ کل سفارش")
    created_at = models.DateTimeField(verbose_name="تاریخ ثبت سفارش")
    products = models.ManyToManyField(Product, through='OrderItem', verbose_name="محصولات")

    def __str__(self):
        return f"سفارش {self.order_id_woocommerce} برای {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, verbose_name="تعداد")
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت در زمان خرید")

class Recommendation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول مرتبط")
    recommendation_text = models.TextField(verbose_name="متن پیشنهاد")
    reason = models.CharField(max_length=255, verbose_name="دلیل پیشنهاد", help_text="مثال: کاهش فروش، موجودی رو به اتمام")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    def __str__(self):
        return f"پیشنهاد برای {self.product.name}"
