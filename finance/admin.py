from django.contrib import admin

from .models import IncomeExpense, Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'title',
        'partner_name',
        'company',
        'status',
        'amount',
        'issue_date',
        'due_date',
        'created_by',
    )
    search_fields = (
        'invoice_number',
        'title',
        'partner_name',
        'company__name',
        'created_by__username',
    )
    list_filter = (
        'company',
        'status',
        'issue_date',
        'due_date',
    )


@admin.register(IncomeExpense)
class IncomeExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'type',
        'amount',
        'category',
        'company',
        'date',
        'created_by',
    )
    search_fields = (
        'category',
        'description',
        'company__name',
        'created_by__username',
    )
    list_filter = (
        'company',
        'type',
        'date',
    )