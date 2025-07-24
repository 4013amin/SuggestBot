from django.contrib import admin
from .models import Product, ProductEvent, Recommendation, ApiKey, OTPCode


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    سفارشی‌سازی نمایش محصولات در پنل ادمین
    """
    list_display = ('name', 'owner', 'price', 'created_at')
    list_filter = ('owner',)
    search_fields = ('name', 'page_url', 'owner__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    """
    سفارشی‌سازی نمایش رویدادهای محصولات
    """
    list_display = ('product', 'get_event_type_display', 'created_at')
    list_filter = ('event_type', 'product__owner__username')
    search_fields = ('product__name',)
    ordering = ('-created_at',)

    # برای خوانایی بهتر عنوان ستون
    def get_event_type_display(self, obj):
        return obj.get_event_type_display()

    get_event_type_display.short_description = 'نوع رویداد'


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    """
    سفارشی‌سازی نمایش پیشنهادها
    """
    list_display = ('product', 'owner', 'get_reason_display', 'is_active', 'created_at')
    list_filter = ('reason', 'is_active', 'owner__username')
    search_fields = ('product__name', 'text')
    ordering = ('-created_at',)
    list_editable = ('is_active',)

    def get_reason_display(self, obj):
        return obj.get_reason_display()

    get_reason_display.short_description = 'دلیل پیشنهاد'


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """
    نمایش کلیدهای API (فقط خواندنی برای امنیت)
    """
    list_display = ('user', 'get_partial_key', 'created_at')
    readonly_fields = ('user', 'key', 'created_at', 'get_partial_key')
    search_fields = ('user__username',)

    def get_partial_key(self, obj):
        # نمایش بخشی از کلید برای امنیت
        return f"{obj.key[:8]}..."

    get_partial_key.short_description = 'کلید API'

    def has_add_permission(self, request):
        # جلوگیری از ساخت کلید از طریق پنل ادمین (چون خودکار ساخته می‌شود)
        return False


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """
    نمایش کدهای یکبار مصرف (فقط خواندنی برای دیباگ)
    """
    list_display = ('user', 'code', 'created_at', 'is_valid')
    readonly_fields = ('user', 'code', 'created_at')
    search_fields = ('user__username',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False