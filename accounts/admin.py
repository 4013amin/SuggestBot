from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, Store, OTPCode


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_public')
    search_fields = ('name',)
    list_filter = ('is_public',)
    ordering = ('-duration_days',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    search_fields = ('user__username', 'plan__name')
    list_filter = ('plan', 'start_date', 'end_date')
    readonly_fields = ('start_date', 'end_date', 'is_active')
    ordering = ('-start_date',)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'site_url', 'is_active', 'last_sync_time', 'created_at')
    search_fields = ('name', 'owner__username', 'site_url')
    list_filter = ('is_active', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_sync_time')


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'is_valid_display')
    search_fields = ('user__username', 'code')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    # برای نمایش وضعیت اعتبار کد به صورت Boolean
    def is_valid_display(self, obj):
        return obj.is_valid()
    is_valid_display.boolean = True
    is_valid_display.short_description = 'معتبر؟'

