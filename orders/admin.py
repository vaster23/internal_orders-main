from django.contrib import admin

from .models import InternalOrder, InternalOrderItem, OrderStatusLog


class InternalOrderItemInline(admin.TabularInline):
    model = InternalOrderItem
    extra = 0


class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ('changed_by', 'old_status', 'new_status', 'comment', 'created_at')
    can_delete = False


@admin.register(InternalOrder)
class InternalOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_code',
        'company',
        'source_branch',
        'destination_branch',
        'status',
        'priority',
        'assigned_driver',
        'created_at',
    )
    list_filter = ('company', 'status', 'priority', 'source_branch', 'destination_branch')
    search_fields = ('order_code', 'source_branch__name', 'destination_branch__name')
    inlines = [InternalOrderItemInline, OrderStatusLogInline]


@admin.register(InternalOrderItem)
class InternalOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity')
    search_fields = ('order__order_code', 'product__name')


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('order__order_code', 'comment')