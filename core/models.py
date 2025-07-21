from django.db import models
from accounts.models import Store
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ProductCategory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='categories')
    woocommerce_id = models.PositiveIntegerField(_("شناسه ووکامرس"))
    name = models.CharField(_("نام"), max_length=255)
    slug = models.SlugField(_("اسلاگ"), max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('store', 'woocommerce_id')
        verbose_name = _("دسته‌بندی محصول")
        verbose_name_plural = _("دسته‌بندی‌های محصولات")


class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    woocommerce_id = models.PositiveIntegerField(_("شناسه ووکامرس"))
    name = models.CharField(_("نام"), max_length=255)
    slug = models.SlugField(_("اسلاگ"), max_length=255)
    permalink = models.URLField(_("لینک محصول"))

    status = models.CharField(_("وضعیت"), max_length=20, default='publish')
    price = models.DecimalField(_("قیمت"), max_digits=12, decimal_places=2, default=0)
    regular_price = models.DecimalField(_("قیمت اصلی"), max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(_("قیمت فروش ویژه"), max_digits=12, decimal_places=2, null=True, blank=True)
    on_sale = models.BooleanField(_("در فروش ویژه؟"), default=False)
    total_sales = models.PositiveIntegerField(_("تعداد کل فروش"), default=0)
    stock_quantity = models.IntegerField(_("موجودی انبار"), null=True, blank=True)
    stock_status = models.CharField(_("وضعیت موجودی"), max_length=20, default='instock')
    categories = models.ManyToManyField(ProductCategory, related_name='products', blank=True)

    created_at_in_wc = models.DateTimeField(_("زمان ایجاد در ووکامرس"))
    updated_at_in_wc = models.DateTimeField(_("زمان به‌روزرسانی در ووکامرس"))

    class Meta:
        unique_together = ('store', 'woocommerce_id')
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering = ['-total_sales']

    def __str__(self):
        return self.name


class Order(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    woocommerce_id = models.PositiveIntegerField(_("شناسه ووکامرس"))
    status = models.CharField(_("وضعیت سفارش"), max_length=50)
    total_amount = models.DecimalField(_("مبلغ کل"), max_digits=12, decimal_places=2)

    created_at_in_wc = models.DateTimeField(_("زمان ایجاد در ووکامرس"))

    class Meta:
        unique_together = ('store', 'woocommerce_id')
        verbose_name = _("سفارش")
        verbose_name_plural = _("سفارشات")
        ordering = ['-created_at_in_wc']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    woocommerce_product_id = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(_("تعداد"))
    price_at_purchase = models.DecimalField(_("قیمت در زمان خرید"), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("آیتم سفارش")
        verbose_name_plural = _("آیتم‌های سفارش")
