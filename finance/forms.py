from django import forms

from .models import IncomeExpense, Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'title',
            'invoice_number',
            'partner_name',
            'amount',
            'issue_date',
            'due_date',
            'status',
            'notes',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'invoice_number': forms.TextInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'partner_name': forms.TextInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-2xl border px-4 py-3'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-2xl border px-4 py-3'}),
            'status': forms.Select(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'notes': forms.Textarea(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
        }


class IncomeExpenseForm(forms.ModelForm):
    class Meta:
        model = IncomeExpense
        fields = [
            'type',
            'amount',
            'category',
            'description',
            'date',
        ]
        widgets = {
            'type': forms.Select(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'category': forms.TextInput(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-2xl border px-4 py-3'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-2xl border px-4 py-3'}),
        }