from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class InternalOrder(models.Model):
    STATUS_SUBMITTED = 'submitted'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_READY_FOR_PICKUP = 'ready_for_pickup'
    STATUS_PICKED_UP = 'picked_up'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Υποβλήθηκε'),
        (STATUS_IN_PROGRESS, 'Σε προετοιμασία'),
        (STATUS_READY_FOR_PICKUP, 'Έτοιμη για παραλαβή'),
        (STATUS_PICKED_UP, 'Καθ’ οδόν'),
        (STATUS_DELIVERED, 'Παραδόθηκε'),
        (STATUS_CANCELLED, 'Ακυρώθηκε'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Χαμηλή'),
        (PRIORITY_NORMAL, 'Κανονική'),
        (PRIORITY_HIGH, 'Υψηλή'),
        (PRIORITY_URGENT, 'Επείγουσα'),
    ]

    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True,
    )
    order_code = models.CharField(max_length=30, unique=True, blank=True)
    source_branch = models.ForeignKey(
        'products.Branch',
        on_delete=models.CASCADE,
        related_name='orders_from_branch'
    )
    destination_branch = models.ForeignKey(
        'products.Branch',
        on_delete=models.CASCADE,
        related_name='orders_to_branch'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders'
    )
    assigned_driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL
    )

    notes = models.TextField(blank=True, default='')
    internal_notes = models.TextField(blank=True, default='')

    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    estimated_arrival = models.DateTimeField(null=True, blank=True)

    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_code:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_code = f'ORD-{timestamp}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_code


class InternalOrderItem(models.Model):
    order = models.ForeignKey(
        InternalOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.order.order_code} - {self.product.name}'


class OrderStatusLog(models.Model):
    order = models.ForeignKey(
        InternalOrder,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    old_status = models.CharField(max_length=30, blank=True, default='')
    new_status = models.CharField(max_length=30)
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_code} - {self.new_status}'