# from django.contrib import admin
#
# # Register your models here.
# from django.contrib import admin
# from .models import ProductCategory, Product, Order, OrderItem, OTPCode, ApiKey
#
#
# @admin.register(ProductCategory)
# class ProductCategoryAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'store', 'woocommerce_id')
#     list_filter = ('store',)
#     search_fields = ('name', 'slug')
#     ordering = ('store', 'name')
#
#
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'store', 'price', 'on_sale', 'total_sales', 'stock_quantity', 'status')
#     list_filter = ('store', 'on_sale', 'status', 'stock_status')
#     search_fields = ('name', 'slug', 'permalink')
#     filter_horizontal = ('categories',)
#     readonly_fields = ('created_at_in_wc', 'updated_at_in_wc')
#     ordering = ('-total_sales',)
#
#
# class OrderItemInline(admin.TabularInline):
#     model = OrderItem
#     extra = 0
#     readonly_fields = ('product', 'woocommerce_product_id', 'quantity', 'price_at_purchase')
#
#
# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('id', 'woocommerce_id', 'store', 'status', 'total_amount', 'created_at_in_wc')
#     list_filter = ('store', 'status')
#     search_fields = ('woocommerce_id',)
#     ordering = ('-created_at_in_wc',)
#     inlines = [OrderItemInline]
#
#
# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ('id', 'order', 'product', 'quantity', 'price_at_purchase')
#     list_filter = ('order__store',)
#     search_fields = ('order__woocommerce_id', 'product__name')
#
#
# @admin.register(OTPCode)
# class OTPCodeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'user', 'code', 'created_at')
#     search_fields = ('user__username', 'code')
#     readonly_fields = ('created_at',)
#
#
# @admin.register(ApiKey)
# class ApiKeyAdmin(admin.ModelAdmin):
#     list_display = ('id', 'user', 'key', 'created_at')
#     search_fields = ('user__username', 'key')
#     readonly_fields = ('created_at', 'key')
