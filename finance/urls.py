from django.urls import path

from . import views

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/add/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:invoice_id>/delete/', views.invoice_delete, name='invoice_delete'),

    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/export/pdf/', views.export_financial_pdf, name='export_financial_pdf'),

    path('income-expenses/', views.income_expense_list, name='income_expense_list'),
    path('income-expenses/add/', views.income_expense_create, name='income_expense_create'),
    path('income-expenses/<int:entry_id>/edit/', views.income_expense_edit, name='income_expense_edit'),
    path('income-expenses/<int:entry_id>/delete/', views.income_expense_delete, name='income_expense_delete'),
]