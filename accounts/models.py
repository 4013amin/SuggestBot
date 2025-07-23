from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# Create your models here.

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('نام طرح'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت (تومان)")
    duration_days = models.IntegerField(verbose_name="مدت زمان (روز)")
    is_public = models.BooleanField(default=True, help_text="آیا این طرح برای خرید در دسترس کاربران باشد؟")
    is_trial = models.BooleanField(default=False, help_text="آیا این یک پلن آزمایشی است که فقط یکبار به کاربر داده می‌شود؟")

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateTimeField(verbose_name="تاریخ شروع")
    end_date = models.DateTimeField(verbose_name="تاریخ انقضا")

    @property
    def is_active(self):
        return self.end_date > timezone.now()

    def __str__(self):
        return f"Subscription for {self.user.username} (Plan: {self.plan.name if self.plan else 'None'})"


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


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (timezone.now() - self.created_at).total_seconds() < 120
