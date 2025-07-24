from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Product, Order, OrderItem, Recommendation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_quantity', 'product_id_woocommerce')
    search_fields = ('name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id_woocommerce', 'customer_name', 'total_price', 'created_at')
    inlines = [OrderItemInline]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('product', 'reason', 'created_at', 'is_active')
    list_filter = ('is_active', 'reason')
