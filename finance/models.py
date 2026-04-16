from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Company


class Invoice(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Εκκρεμεί'),
        (STATUS_PAID, 'Πληρώθηκε'),
        (STATUS_OVERDUE, 'Ληξιπρόθεσμο'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_invoices')

    title = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=100)
    partner_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.partner_name}"

    @property
    def computed_status(self):
        if self.status == self.STATUS_PAID:
            return self.STATUS_PAID

        if self.status == self.STATUS_PENDING and self.due_date and self.due_date < timezone.localdate():
            return self.STATUS_OVERDUE

        return self.status

    @property
    def computed_status_label(self):
        mapping = {
            self.STATUS_PENDING: 'Εκκρεμεί',
            self.STATUS_PAID: 'Πληρώθηκε',
            self.STATUS_OVERDUE: 'Ληξιπρόθεσμο',
        }
        return mapping.get(self.computed_status, self.get_status_display())


class IncomeExpense(models.Model):
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'

    TYPE_CHOICES = [
        (TYPE_INCOME, 'Έσοδο'),
        (TYPE_EXPENSE, 'Έξοδο'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='income_expenses')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='income_expenses')

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    category = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount}€ - {self.date}"