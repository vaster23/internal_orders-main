import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.utils import (
    create_audit_log,
    create_company_notification_for_admins,
    create_company_notification_for_drivers,
    create_notification,
)
from core.models import UserBranch, UserCompany
from products.models import Branch, Category, Product

from .models import InternalOrder, InternalOrderItem
from .utils import (
    can_manage_order_status,
    create_status_log,
    order_has_map_data,
    set_estimated_arrival,
    user_is_driver,
)


def _get_user_company(user):
    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    return user_company.company if user_company else None


def _attach_order_ui_data(order):
    order.has_map_data = order_has_map_data(order)

    if order.has_map_data:
        order.map_source_lat = float(order.source_branch.latitude)
        order.map_source_lng = float(order.source_branch.longitude)
        order.map_destination_lat = float(order.destination_branch.latitude)
        order.map_destination_lng = float(order.destination_branch.longitude)
        order.map_id = f"map-order-{order.id}"

    return order


def _apply_order_filters(queryset, request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    branch_filter = request.GET.get('branch', '').strip()
    driver_filter = request.GET.get('driver', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search_query:
        queryset = queryset.filter(order_code__icontains=search_query)

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if branch_filter:
        queryset = queryset.filter(source_branch_id=branch_filter) | queryset.filter(destination_branch_id=branch_filter)

    if driver_filter:
        queryset = queryset.filter(assigned_driver_id=driver_filter)

    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset.order_by('-created_at'), {
        'q': search_query,
        'status': status_filter,
        'branch': branch_filter,
        'driver': driver_filter,
        'date_from': date_from,
        'date_to': date_to,
    }


@login_required
def order_shop(request):
    company = _get_user_company(request.user)

    categories = Category.objects.order_by('name')
    products = Product.objects.filter(active=True).select_related(
        'unit',
        'category',
        'branch',
        'branch__company',
    ).order_by('name')

    branches = Branch.objects.select_related('company').order_by('name')
    error = None
    success = None
    notes_value = ''
    priority_value = InternalOrder.PRIORITY_NORMAL
    destination_branch_id = ''
    user_branch = UserBranch.objects.filter(user=request.user).select_related('branch__company').first()

    if company:
        products = products.filter(branch__company=company)
        branches = branches.filter(company=company)

    if request.method == 'POST':
        notes_value = request.POST.get('notes', '').strip()
        priority_value = request.POST.get('priority', InternalOrder.PRIORITY_NORMAL).strip()
        destination_branch_id = request.POST.get('destination_branch', '').strip()
        items_json = request.POST.get('items_json', '').strip()

        if company is None:
            error = 'Ο χρήστης δεν έχει συνδεδεμένη εταιρεία.'
        elif user_branch is None:
            error = 'Ο χρήστης δεν έχει συνδεδεμένο υποκατάστημα.'
        elif user_branch.branch.company_id != company.id:
            error = 'Το υποκατάστημα του χρήστη δεν ανήκει στην εταιρεία του.'
        elif not destination_branch_id:
            error = 'Διάλεξε υποκατάστημα προορισμού.'
        elif not items_json:
            error = 'Το καλάθι είναι κενό.'
        else:
            try:
                destination_branch = Branch.objects.get(id=destination_branch_id, company=company)
            except (Branch.DoesNotExist, ValueError):
                error = 'Το υποκατάστημα προορισμού δεν είναι έγκυρο.'
            else:
                try:
                    submitted_items = json.loads(items_json)
                except json.JSONDecodeError:
                    error = 'Τα στοιχεία της παραγγελίας δεν είναι έγκυρα.'
                else:
                    product_map = {product.id: product for product in products}
                    order_items = []

                    for raw_item in submitted_items:
                        raw_product_id = str(raw_item.get('product_id', '')).strip()
                        raw_quantity = str(raw_item.get('quantity', '')).strip()

                        try:
                            product_id = int(raw_product_id)
                            quantity = Decimal(raw_quantity)
                        except (TypeError, ValueError, InvalidOperation):
                            error = 'Υπάρχει μη έγκυρη ποσότητα σε κάποιο προϊόν.'
                            break

                        if quantity <= 0:
                            continue

                        product = product_map.get(product_id)
                        if product is None:
                            error = 'Κάποιο προϊόν δεν βρέθηκε ή δεν ανήκει στην εταιρεία.'
                            break

                        order_items.append({
                            'product': product,
                            'quantity': quantity,
                        })

                    if not error and not order_items:
                        error = 'Πρόσθεσε τουλάχιστον ένα προϊόν στην παραγγελία.'

                    if not error:
                        with transaction.atomic():
                            order = InternalOrder.objects.create(
                                company=company,
                                source_branch=user_branch.branch,
                                destination_branch=destination_branch,
                                notes=notes_value,
                                created_by=request.user,
                                priority=priority_value,
                                status=InternalOrder.STATUS_SUBMITTED,
                            )

                            InternalOrderItem.objects.bulk_create([
                                InternalOrderItem(
                                    order=order,
                                    product=item['product'],
                                    quantity=item['quantity'],
                                )
                                for item in order_items
                            ])

                            create_status_log(
                                order=order,
                                user=request.user,
                                old_status='',
                                new_status=InternalOrder.STATUS_SUBMITTED,
                                comment='Δημιουργία παραγγελίας',
                            )

                            create_audit_log(
                                user=request.user,
                                company=company,
                                action='create_order',
                                target_type='Order',
                                target_id=order.id,
                                description=f'Δημιουργήθηκε παραγγελία {order.order_code}',
                            )

                            order_url = reverse('orders:order_detail', args=[order.id])

                            create_company_notification_for_admins(
                                company=company,
                                title='Νέα παραγγελία',
                                message=f'Δημιουργήθηκε η παραγγελία {order.order_code}.',
                                url=order_url,
                            )

                        return redirect(f"{reverse('orders:order_shop')}?created={order.id}")

    created_order_id = request.GET.get('created')
    if created_order_id:
        success = 'Η παραγγελία καταχωρίστηκε επιτυχώς.'

    return render(request, 'orders/order_shop.html', {
        'categories': categories,
        'products': products,
        'branches': branches,
        'error': error,
        'success': success,
        'notes_value': notes_value,
        'priority_value': priority_value,
        'destination_branch_id': destination_branch_id,
        'user_branch': user_branch.branch if user_branch else None,
        'priority_choices': InternalOrder.PRIORITY_CHOICES,
    })


@login_required
def order_list(request):
    error = None
    success = None
    company = _get_user_company(request.user)
    current_user_branch = UserBranch.objects.filter(user=request.user).select_related('branch').first()
    current_user_branch_id = current_user_branch.branch_id if current_user_branch else None
    is_driver = user_is_driver(request.user)

    if request.method == 'POST' and can_manage_order_status(request.user):
        order_id = request.POST.get('order_id', '').strip()
        new_status = request.POST.get('status', '').strip()

        try:
            order = InternalOrder.objects.get(id=order_id, company=company)
        except (InternalOrder.DoesNotExist, ValueError):
            error = 'Η παραγγελία δεν βρέθηκε.'
        else:
            valid_statuses = {choice[0] for choice in InternalOrder.STATUS_CHOICES}
            if new_status not in valid_statuses:
                error = 'Το status δεν είναι έγκυρο.'
            else:
                old_status = order.status
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])

                create_status_log(
                    order=order,
                    user=request.user,
                    old_status=old_status,
                    new_status=new_status,
                    comment='Αλλαγή κατάστασης από διαχειριστή',
                )

                create_audit_log(
                    user=request.user,
                    company=company,
                    action='update_order_status',
                    target_type='Order',
                    target_id=order.id,
                    description=f'Η παραγγελία {order.order_code} άλλαξε από {old_status} σε {new_status}',
                )

                order_url = reverse('orders:order_detail', args=[order.id])

                if order.created_by:
                    create_notification(
                        user=order.created_by,
                        company=company,
                        title='Ενημέρωση παραγγελίας',
                        message=f'Η παραγγελία {order.order_code} άλλαξε κατάσταση.',
                        url=order_url,
                    )

                if order.assigned_driver:
                    create_notification(
                        user=order.assigned_driver,
                        company=company,
                        title='Ενημέρωση delivery',
                        message=f'Η παραγγελία {order.order_code} ενημερώθηκε.',
                        url=order_url,
                    )

                return redirect(f"{reverse('orders:order_list')}?updated={order.id}")

    orders = InternalOrder.objects.select_related(
        'company',
        'source_branch',
        'destination_branch',
        'created_by',
        'assigned_driver',
    ).prefetch_related(
        'items__product__unit',
        'items__product__branch',
        'status_logs',
    )

    if company:
        orders = orders.filter(company=company)
    else:
        orders = orders.none()

    orders, filters = _apply_order_filters(orders, request)

    updated_order_id = request.GET.get('updated')
    if updated_order_id:
        success = 'Η κατάσταση της παραγγελίας ενημερώθηκε.'

    branches = Branch.objects.order_by('name')
    drivers = User.objects.filter(groups__name='driver').distinct()

    if company:
        branches = branches.filter(company=company)
        drivers = drivers.filter(user_company__company=company)

    if is_driver:
        available_pickups = list(orders.filter(
            status=InternalOrder.STATUS_READY_FOR_PICKUP
        ))
        active_deliveries = list(orders.filter(
            status=InternalOrder.STATUS_PICKED_UP,
            assigned_driver=request.user,
        ))
        completed_deliveries = list(orders.filter(
            status=InternalOrder.STATUS_DELIVERED,
            assigned_driver=request.user,
        )[:10])

        for order in available_pickups + active_deliveries + completed_deliveries:
            order.visible_items = list(order.items.all())
            _attach_order_ui_data(order)

        return render(request, 'orders/order_list.html', {
            'error': error,
            'success': success,
            'is_driver': True,
            'available_pickups': available_pickups,
            'active_deliveries': active_deliveries,
            'completed_deliveries': completed_deliveries,
            'status_choices': InternalOrder.STATUS_CHOICES,
            'branches': branches,
            'drivers': drivers,
            'filters': filters,
        })

    orders = list(orders)
    for order in orders:
        if current_user_branch:
            order.visible_items = [
                item for item in order.items.all()
                if item.product.branch_id == current_user_branch_id
            ] or list(order.items.all())
        else:
            order.visible_items = list(order.items.all())

        _attach_order_ui_data(order)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'status_choices': InternalOrder.STATUS_CHOICES,
        'error': error,
        'success': success,
        'current_user_branch_id': current_user_branch_id,
        'current_user_branch': current_user_branch.branch if current_user_branch else None,
        'is_driver': False,
        'can_manage_status': can_manage_order_status(request.user),
        'branches': branches,
        'drivers': drivers,
        'filters': filters,
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        InternalOrder.objects.select_related(
            'source_branch',
            'destination_branch',
            'assigned_driver',
            'created_by',
            'company',
        ).prefetch_related(
            'items__product',
            'status_logs',
        ),
        id=order_id
    )

    if hasattr(request.user, 'user_company'):
        if order.company != request.user.user_company.company:
            return render(request, 'errors/403.html', status=403)

    timeline = [
        ('submitted', 'Υποβλήθηκε'),
        ('in_progress', 'Σε προετοιμασία'),
        ('ready_for_pickup', 'Έτοιμη για παραλαβή'),
        ('picked_up', 'Σε διαδρομή'),
        ('delivered', 'Παραδόθηκε'),
    ]

    order.visible_items = list(order.items.all())

    eta_status = None
    now = timezone.now()

    if order.status == 'picked_up' and order.estimated_arrival:
        if now > order.estimated_arrival:
            eta_status = 'delayed'
        else:
            eta_status = 'on_time'
    elif order.status == 'delivered' and order.delivered_at and order.estimated_arrival:
        if order.delivered_at <= order.estimated_arrival:
            eta_status = 'delivered_on_time'
        else:
            eta_status = 'delivered_late'

    create_audit_log(
        user=request.user,
        company=order.company,
        action='view_order',
        target_type='Order',
        target_id=order.id,
        description=f'Προβολή παραγγελίας {order.order_code}'
    )

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'timeline': timeline,
        'eta_status': eta_status,
    })


@login_required
def export_orders_csv(request):
    company = _get_user_company(request.user)

    if not can_manage_order_status(request.user):
        return redirect('orders:order_list')

    orders = InternalOrder.objects.select_related(
        'company',
        'source_branch',
        'destination_branch',
        'created_by',
        'assigned_driver',
    )

    if company:
        orders = orders.filter(company=company)
    else:
        orders = orders.none()

    orders, _ = _apply_order_filters(orders, request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order Code',
        'Company',
        'Source Branch',
        'Destination Branch',
        'Status',
        'Priority',
        'Created By',
        'Assigned Driver',
        'Created At',
        'Picked Up At',
        'Delivered At',
        'Estimated Minutes',
    ])

    for order in orders:
        writer.writerow([
            order.order_code,
            order.company.name if order.company else '',
            order.source_branch.name if order.source_branch else '',
            order.destination_branch.name if order.destination_branch else '',
            order.get_status_display(),
            order.get_priority_display(),
            order.created_by.username if order.created_by else '',
            order.assigned_driver.username if order.assigned_driver else '',
            order.created_at.strftime('%d/%m/%Y %H:%M') if order.created_at else '',
            order.picked_up_at.strftime('%d/%m/%Y %H:%M') if order.picked_up_at else '',
            order.delivered_at.strftime('%d/%m/%Y %H:%M') if order.delivered_at else '',
            order.estimated_minutes or '',
        ])

    return response


@login_required
def driver_pickup_order(request, order_id):
    company = _get_user_company(request.user)

    if request.method != 'POST' or not user_is_driver(request.user):
        return redirect('orders:order_list')

    order = get_object_or_404(InternalOrder, id=order_id, company=company)

    if order.status == InternalOrder.STATUS_READY_FOR_PICKUP:
        old_status = order.status
        order.status = InternalOrder.STATUS_PICKED_UP
        order.assigned_driver = request.user
        order.picked_up_at = timezone.now()
        set_estimated_arrival(order)
        order.save(update_fields=[
            'status',
            'assigned_driver',
            'picked_up_at',
            'estimated_arrival',
            'estimated_minutes',
            'updated_at',
        ])

        create_status_log(
            order=order,
            user=request.user,
            old_status=old_status,
            new_status=InternalOrder.STATUS_PICKED_UP,
            comment='Παραλαβή από οδηγό',
        )

        create_audit_log(
            user=request.user,
            company=company,
            action='pickup_order',
            target_type='Order',
            target_id=order.id,
            description=f'Ο driver παρέλαβε την παραγγελία {order.order_code}',
        )

        order_url = reverse('orders:order_detail', args=[order.id])

        if order.created_by:
            create_notification(
                user=order.created_by,
                company=company,
                title='Η παραγγελία παραλήφθηκε',
                message=f'Η παραγγελία {order.order_code} παραλήφθηκε από οδηγό.',
                url=order_url,
            )

        create_company_notification_for_admins(
            company=company,
            title='Παραλαβή παραγγελίας',
            message=f'Η παραγγελία {order.order_code} είναι πλέον σε διαδρομή.',
            url=order_url,
        )

    return redirect('orders:order_list')


@login_required
def driver_deliver_order(request, order_id):
    company = _get_user_company(request.user)

    if request.method != 'POST' or not user_is_driver(request.user):
        return redirect('orders:order_list')

    order = get_object_or_404(
        InternalOrder,
        id=order_id,
        company=company,
        assigned_driver=request.user,
    )

    if order.status == InternalOrder.STATUS_PICKED_UP:
        old_status = order.status
        order.status = InternalOrder.STATUS_DELIVERED
        order.delivered_at = timezone.now()
        order.save(update_fields=[
            'status',
            'delivered_at',
            'updated_at',
        ])

        create_status_log(
            order=order,
            user=request.user,
            old_status=old_status,
            new_status=InternalOrder.STATUS_DELIVERED,
            comment='Παράδοση από οδηγό',
        )

        create_audit_log(
            user=request.user,
            company=company,
            action='deliver_order',
            target_type='Order',
            target_id=order.id,
            description=f'Ο driver παρέδωσε την παραγγελία {order.order_code}',
        )

        order_url = reverse('orders:order_detail', args=[order.id])

        if order.created_by:
            create_notification(
                user=order.created_by,
                company=company,
                title='Η παραγγελία παραδόθηκε',
                message=f'Η παραγγελία {order.order_code} ολοκληρώθηκε.',
                url=order_url,
            )

        create_company_notification_for_admins(
            company=company,
            title='Ολοκλήρωση παράδοσης',
            message=f'Η παραγγελία {order.order_code} παραδόθηκε επιτυχώς.',
            url=order_url,
        )

    return redirect('orders:order_list')