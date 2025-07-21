from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import Store
from core.models import Product


# Create your models here.
class Recommendation(models.Model):
    class ReasonCodes(models.TextChoices):
        SALES_DROP = 'SALES_DROP', _('افت فروش')
        LOW_SALES = 'LOW_SALES', _('فروش پایین مزمن')
        NO_SALES = 'NO_SALES', _('بدون فروش')
        HIGH_POTENTIAL = 'HIGH_POTENTIAL', _('پتانسیل بالای فروش')
        POOR_CONVERSION = 'POOR_CONVERSION', _('نرخ تبدیل پایین')
        RELATED_PRODUCT_OPP = 'RELATED_PRODUCT_OPP', _('فرصت فروش همراه')
        STOCK_ISSUE = 'STOCK_ISSUE', _('مشکل موجودی انبار')

    class Status(models.TextChoices):
        NEW = 'new', _('جدید')
        SEEN = 'seen', _('مشاهده شده')
        ACTIONED = 'actioned', _('اقدام شده')
        DISMISSED = 'dismissed', _('نادیده گرفته شده')

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )

    reason_code = models.CharField(
        _("کد دلیل"),
        max_length=50,
        choices=ReasonCodes.choices
    )

    reason_code = models.CharField(
        _("کد دلیل"),
        max_length=50,
        choices=ReasonCodes.choices
    )
    suggestion = models.TextField(
        _("متن پیشنهاد"),
        help_text=_("یک اقدام عملی که فروشنده باید انجام دهد.")
    )
    details = models.JSONField(
        _("جزئیات تحلیلی"),
        default=dict,
        help_text=_("داده‌هایی که منجر به این پیشنهاد شده‌اند، برای نمایش در UI.")
    )
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True  # برای فیلتر کردن سریعتر
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))

    class Meta:
        verbose_name = _("پیشنهاد")
        verbose_name_plural = _("پیشنهادها")
        ordering = ['-created_at']
        # یک محصول در یک فروشگاه نباید دو پیشنهاد فعال با یک دلیل مشابه داشته باشد
        unique_together = ('product', 'reason_code', 'status')
