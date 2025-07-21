from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Store(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='stores',
        verbose_name=_("صاحب فروشگاه")
    )

    name = models.CharField(max_length=200, verbose_name="نام فروشگاه")
    site_url = models.URLField(unique=True, verbose_name="آدرس سایت ها", help_text=_("مثال: https://my-shop.com"))
    woocommerce_consumer_key = models.CharField(max_length=255, verbose_name="کلید ووکامرس ")
    woocommerce_consumer_secret = models.CharField(max_length=255, verbose_name="کلید امنیتی ووکامرس ")
    is_active = models.BooleanField(default=True, verbose_name="اشتراک فعال ", help_text=(
        "در صورت غیرفعال بودن، همگام‌سازی و تحلیل برای این فروشگاه انجام نمی‌شود."))
    last_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="آخرین زمان همگام سازی موفق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("زمان به‌روزرسانی"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("فروشگاه")
        verbose_name_plural = _("فروشگاه‌ها")
        ordering = ['-created_at']
