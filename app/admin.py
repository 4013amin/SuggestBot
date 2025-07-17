from django.contrib import admin
from . import models


# Register your models here.
@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'source_id')
    search_fields = ('name', 'source_id')

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    
    
@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id' , 'user')
