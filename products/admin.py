from django.contrib import admin

from .models import Branch, Category, Product, Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company', 'active')
    search_fields = ('name', 'code', 'company__name')
    list_filter = ('company', 'active')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'active')
    search_fields = ('name', 'company__name')
    list_filter = ('company', 'active')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'address', 'active', 'latitude', 'longitude')
    search_fields = ('name', 'company__name', 'address')
    list_filter = ('company', 'active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'category', 'unit', 'active')
    search_fields = ('name', 'branch__name', 'category__name', 'unit__name')
    list_filter = ('active', 'branch', 'category')