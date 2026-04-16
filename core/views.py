from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from finance.models import IncomeExpense, Invoice
from orders.models import InternalOrder
from products.models import Branch, Category, Unit

from .forms import (
    AdminResetPasswordForm,
    CompanyOnboardingForm,
    CompanySettingsForm,
    ForcePasswordChangeForm,
)
from .models import Company, Notification, UserBranch, UserCompany, UserProfile


def get_company(user):
    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    return user_company.company if user_company else None


def _users_with_branch_and_company(current_company=None):
    users = User.objects.select_related(
        'user_branch__branch',
        'user_company__company',
        'profile',
    ).prefetch_related('groups').order_by('username')

    if current_company:
        users = users.filter(user_company__company=current_company)

    for user in users:
        user.assigned_branch = getattr(getattr(user, 'user_branch', None), 'branch', None)
        user.assigned_company = getattr(getattr(user, 'user_company', None), 'company', None)
        user.role_names = ', '.join(group.name for group in user.groups.all())
        user.must_change_password_value = getattr(getattr(user, 'profile', None), 'must_change_password', False)

    return users


@login_required
def force_password_change(request):
    if request.user.is_superuser:
        return redirect('home')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.must_change_password:
        return redirect('home')

    if request.method == 'POST':
        form = ForcePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            request.user.set_password(new_password)
            request.user.save()

            profile.must_change_password = False
            profile.save(update_fields=['must_change_password'])

            update_session_auth_hash(request, request.user)
            return redirect('home')
    else:
        form = ForcePasswordChangeForm(user=request.user)

    return render(request, 'core/force_password_change.html', {
        'form': form,
    })


def company_inactive(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('home')

    if not request.user.is_authenticated:
        return redirect('login')

    user_company = UserCompany.objects.filter(user=request.user).select_related('company').first()

    if user_company and user_company.company.active:
        return redirect('home')

    return render(request, 'core/company_inactive.html', {
        'company': user_company.company if user_company else None,
    })


@login_required
def home(request):
    user = request.user

    if user.is_superuser:
        companies = Company.objects.all().order_by('name')

        company_rows = []
        for company in companies:
            users_count = User.objects.filter(user_company__company=company).distinct().count()
            branches_count = Branch.objects.filter(company=company).count()
            orders_count = InternalOrder.objects.filter(company=company).count()
            drivers_count = User.objects.filter(
                user_company__company=company,
                groups__name='driver'
            ).distinct().count()
            invoices_count = Invoice.objects.filter(company=company).count()
            finance_entries_count = IncomeExpense.objects.filter(company=company).count()

            if orders_count == 0:
                health = 'inactive'
            elif orders_count < 10:
                health = 'low'
            elif orders_count < 50:
                health = 'medium'
            else:
                health = 'high'

            company_rows.append({
                'company': company,
                'users_count': users_count,
                'branches_count': branches_count,
                'orders_count': orders_count,
                'drivers_count': drivers_count,
                'invoices_count': invoices_count,
                'finance_entries_count': finance_entries_count,
                'health': health,
            })

        top_companies = sorted(company_rows, key=lambda x: x['orders_count'], reverse=True)[:5]
        newest_companies = companies.order_by('-created_at')[:5]

        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:8]
        unread_notifications_count = Notification.objects.filter(user=user, is_read=False).count()

        return render(request, 'core/platform_home.html', {
            'platform_mode': True,
            'notifications': notifications,
            'unread_notifications_count': unread_notifications_count,
            'total_companies': companies.count(),
            'active_companies': companies.filter(active=True).count(),
            'inactive_companies': companies.filter(active=False).count(),
            'total_users': User.objects.filter(user_company__isnull=False).distinct().count(),
            'total_branches': Branch.objects.count(),
            'total_orders': InternalOrder.objects.count(),
            'total_drivers': User.objects.filter(groups__name='driver').distinct().count(),
            'total_invoices': Invoice.objects.count(),
            'total_finance_entries': IncomeExpense.objects.count(),
            'top_companies': top_companies,
            'newest_companies': newest_companies,
        })

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.must_change_password:
        return redirect('force_password_change')

    company = get_company(user)
    is_admin = user.groups.filter(name='admin').exists()
    is_driver = user.groups.filter(name='driver').exists()

    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:8]
    unread_notifications_count = Notification.objects.filter(user=user, is_read=False).count()

    context = {
        'company': company,
        'is_admin': is_admin,
        'is_driver': is_driver,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }

    if is_admin and company:
        company_orders = InternalOrder.objects.filter(company=company)
        finance_entries = IncomeExpense.objects.filter(company=company)
        admin_invoices = Invoice.objects.filter(company=company)

        total_income = finance_entries.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        total_expense = finance_entries.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        overdue_invoices = sum(1 for inv in admin_invoices if inv.computed_status == 'overdue')
        pending_invoices = sum(1 for inv in admin_invoices if inv.computed_status == 'pending')

        context.update({
            'total_orders': company_orders.count(),
            'ready_for_pickup_orders': company_orders.filter(
                status=InternalOrder.STATUS_READY_FOR_PICKUP
            ).count(),
            'picked_up_orders': company_orders.filter(
                status=InternalOrder.STATUS_PICKED_UP
            ).count(),
            'delivered_orders': company_orders.filter(
                status=InternalOrder.STATUS_DELIVERED
            ).count(),
            'recent_orders': company_orders.select_related(
                'source_branch',
                'destination_branch',
                'assigned_driver',
            ).order_by('-created_at')[:5],
            'home_total_income': total_income,
            'home_total_expense': total_expense,
            'home_net': total_income - total_expense,
            'home_pending_invoices': pending_invoices,
            'home_overdue_invoices': overdue_invoices,
        })

    elif is_driver and company:
        driver_orders = InternalOrder.objects.filter(
            company=company,
            assigned_driver=user
        )

        context.update({
            'driver_active_orders': driver_orders.filter(
                status=InternalOrder.STATUS_PICKED_UP
            ),
            'driver_completed_orders': driver_orders.filter(
                status=InternalOrder.STATUS_DELIVERED
            )[:5],
        })

    elif company:
        my_orders = InternalOrder.objects.filter(
            company=company,
            created_by=user
        ).order_by('-created_at')

        context.update({
            'my_total_orders': my_orders.count(),
            'my_open_orders': my_orders.exclude(
                status__in=[InternalOrder.STATUS_DELIVERED, InternalOrder.STATUS_CANCELLED]
            ).count(),
            'my_delivered_orders': my_orders.filter(
                status=InternalOrder.STATUS_DELIVERED
            ).count(),
            'my_recent_orders': my_orders[:5],
        })

    return render(request, 'core/index.html', context)


@login_required
def dashboard(request):
    company = get_company(request.user)

    if request.user.is_superuser:
        companies = Company.objects.all().order_by('name')

        company_rows = []
        for company_obj in companies:
            users_count = User.objects.filter(user_company__company=company_obj).distinct().count()
            branches_count = Branch.objects.filter(company=company_obj).count()
            orders_count = InternalOrder.objects.filter(company=company_obj).count()
            drivers_count = User.objects.filter(
                user_company__company=company_obj,
                groups__name='driver'
            ).distinct().count()
            invoices_count = Invoice.objects.filter(company=company_obj).count()

            if orders_count == 0:
                health = 'inactive'
            elif orders_count < 10:
                health = 'low'
            elif orders_count < 50:
                health = 'medium'
            else:
                health = 'high'

            company_rows.append({
                'company': company_obj,
                'users_count': users_count,
                'branches_count': branches_count,
                'orders_count': orders_count,
                'drivers_count': drivers_count,
                'invoices_count': invoices_count,
                'health': health,
            })

        return render(request, 'core/platform_analytics.html', {
            'platform_mode': True,
            'total_companies': companies.count(),
            'active_companies': companies.filter(active=True).count(),
            'inactive_companies': companies.filter(active=False).count(),
            'total_users': User.objects.filter(user_company__isnull=False).distinct().count(),
            'total_branches': Branch.objects.count(),
            'total_orders': InternalOrder.objects.count(),
            'total_drivers': User.objects.filter(groups__name='driver').distinct().count(),
            'total_invoices': Invoice.objects.count(),
            'company_rows': sorted(company_rows, key=lambda x: x['orders_count'], reverse=True),
        })

    if company is None:
        return redirect('home')

    company_orders = InternalOrder.objects.filter(company=company)
    company_users = User.objects.filter(user_company__company=company).distinct()
    company_branches = Branch.objects.filter(company=company)
    company_drivers = company_users.filter(groups__name='driver').distinct()

    context = {
        'company': company,
        'total_orders': company_orders.count(),
        'submitted_orders': company_orders.filter(status=InternalOrder.STATUS_SUBMITTED).count(),
        'in_progress_orders': company_orders.filter(status=InternalOrder.STATUS_IN_PROGRESS).count(),
        'ready_for_pickup_orders': company_orders.filter(status=InternalOrder.STATUS_READY_FOR_PICKUP).count(),
        'picked_up_orders': company_orders.filter(status=InternalOrder.STATUS_PICKED_UP).count(),
        'delivered_orders': company_orders.filter(status=InternalOrder.STATUS_DELIVERED).count(),
        'cancelled_orders': company_orders.filter(status=InternalOrder.STATUS_CANCELLED).count(),
        'total_users': company_users.count(),
        'active_users': company_users.filter(is_active=True).count(),
        'total_branches': company_branches.count(),
        'total_drivers': company_drivers.count(),
        'recent_orders': company_orders.select_related(
            'source_branch',
            'destination_branch',
            'created_by',
            'assigned_driver',
        ).order_by('-created_at')[:8],
        'orders_by_destination': company_branches.annotate(
            total_orders=Count('orders_to_branch')
        ).order_by('-total_orders', 'name')[:6],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def analytics_dashboard(request):
    if request.user.is_superuser:
        return redirect('dashboard')

    company = get_company(request.user)

    if company is None:
        return redirect('home')

    company_orders = InternalOrder.objects.filter(company=company)
    delivered_orders = company_orders.filter(
        status=InternalOrder.STATUS_DELIVERED,
        picked_up_at__isnull=False,
        delivered_at__isnull=False,
    )

    delivery_duration_expression = ExpressionWrapper(
        F('delivered_at') - F('picked_up_at'),
        output_field=DurationField(),
    )

    average_delivery_duration = delivered_orders.annotate(
        duration=delivery_duration_expression
    ).aggregate(avg_duration=Avg('duration'))['avg_duration']

    average_eta_minutes = company_orders.filter(
        estimated_minutes__isnull=False
    ).aggregate(avg_eta=Avg('estimated_minutes'))['avg_eta']

    orders_by_source = Branch.objects.filter(company=company).annotate(
        total_orders=Count('orders_from_branch')
    ).order_by('-total_orders', 'name')

    orders_by_destination = Branch.objects.filter(company=company).annotate(
        total_orders=Count('orders_to_branch')
    ).order_by('-total_orders', 'name')

    deliveries_by_driver = User.objects.filter(
        user_company__company=company,
        groups__name='driver'
    ).annotate(
        delivered_count=Count(
            'assigned_orders',
            filter=Q(assigned_orders__status=InternalOrder.STATUS_DELIVERED)
        ),
        active_count=Count(
            'assigned_orders',
            filter=Q(assigned_orders__status=InternalOrder.STATUS_PICKED_UP)
        )
    ).distinct().order_by('-delivered_count', 'username')

    return render(request, 'core/analytics_dashboard.html', {
        'company': company,
        'total_orders': company_orders.count(),
        'submitted_orders': company_orders.filter(status=InternalOrder.STATUS_SUBMITTED).count(),
        'in_progress_orders': company_orders.filter(status=InternalOrder.STATUS_IN_PROGRESS).count(),
        'ready_for_pickup_orders': company_orders.filter(status=InternalOrder.STATUS_READY_FOR_PICKUP).count(),
        'picked_up_orders': company_orders.filter(status=InternalOrder.STATUS_PICKED_UP).count(),
        'delivered_orders': company_orders.filter(status=InternalOrder.STATUS_DELIVERED).count(),
        'cancelled_orders': company_orders.filter(status=InternalOrder.STATUS_CANCELLED).count(),
        'average_eta_minutes': round(average_eta_minutes, 1) if average_eta_minutes else None,
        'average_delivery_duration': average_delivery_duration,
        'orders_by_source': orders_by_source,
        'orders_by_destination': orders_by_destination,
        'deliveries_by_driver': deliveries_by_driver,
    })


@login_required
def company_settings(request):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)
    if company is None:
        return redirect('home')

    success = None

    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            success = 'Οι ρυθμίσεις εταιρείας αποθηκεύτηκαν επιτυχώς.'
    else:
        form = CompanySettingsForm(instance=company)

    return render(request, 'core/company_settings.html', {
        'company': company,
        'form': form,
        'success': success,
    })


@login_required
def users(request):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)

    return render(request, 'core/user_list.html', {
        'users': _users_with_branch_and_company(company) if company else _users_with_branch_and_company(),
        'company': company,
    })


@login_required
def admin_reset_user_password(request, user_id):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = AdminResetPasswordForm(user=user_obj, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_temporary_password']
            user_obj.set_password(new_password)
            user_obj.save()

            UserProfile.objects.update_or_create(
                user=user_obj,
                defaults={'must_change_password': True},
            )

            return render(request, 'core/admin_reset_user_password.html', {
                'user_obj': user_obj,
                'form': AdminResetPasswordForm(user=user_obj),
                'success': 'Ο προσωρινός κωδικός αποθηκεύτηκε επιτυχώς.',
                'company': company,
            })
    else:
        form = AdminResetPasswordForm(user=user_obj)

    return render(request, 'core/admin_reset_user_password.html', {
        'user_obj': user_obj,
        'form': form,
        'company': company,
    })


@login_required
def user_add(request):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)
    branches = Branch.objects.filter(company=company).order_by('name') if company else Branch.objects.none()
    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        branch_id = request.POST.get('branch', '').strip()
        role = request.POST.get('role', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not username or not password or not branch_id or not role:
            error = 'Παρακαλώ συμπληρώστε όλα τα πεδία.'
        elif User.objects.filter(username=username).exists():
            error = 'Το όνομα χρήστη υπάρχει ήδη.'
        else:
            selected_branch = get_object_or_404(Branch, id=branch_id, company=company)
            user = User.objects.create_user(username=username, password=password)
            user.is_active = is_active
            user.is_staff = role == 'admin'
            user.is_superuser = False
            user.save()

            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)

            UserBranch.objects.create(user=user, branch=selected_branch)
            UserCompany.objects.create(user=user, company=company)
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'must_change_password': True},
            )

            return redirect('users')

    return render(request, 'registration/add_user.html', {
        'error': error,
        'branches': branches,
        'company': company,
    })


@login_required
def user_edit(request, user_id):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)
    user_obj = get_object_or_404(User, id=user_id)
    branches = Branch.objects.filter(company=company).order_by('name') if company else Branch.objects.none()
    error = None

    user_branch = getattr(user_obj, 'user_branch', None)
    current_role = user_obj.groups.first().name if user_obj.groups.exists() else 'user'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        branch_id = request.POST.get('branch', '').strip()
        role = request.POST.get('role', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not username or not branch_id or not role:
            error = 'Παρακαλώ συμπληρώστε όνομα χρήστη, ρόλο και υποκατάστημα.'
        elif User.objects.filter(username=username).exclude(id=user_id).exists():
            error = 'Το όνομα χρήστη υπάρχει ήδη.'
        else:
            selected_branch = get_object_or_404(Branch, id=branch_id, company=company)

            user_obj.username = username
            if password:
                user_obj.set_password(password)
                UserProfile.objects.update_or_create(
                    user=user_obj,
                    defaults={'must_change_password': True},
                )

            user_obj.is_active = is_active
            user_obj.is_staff = role == 'admin'
            user_obj.is_superuser = False
            user_obj.save()

            user_obj.groups.clear()
            group, _ = Group.objects.get_or_create(name=role)
            user_obj.groups.add(group)

            UserBranch.objects.update_or_create(
                user=user_obj,
                defaults={'branch': selected_branch},
            )
            UserCompany.objects.update_or_create(
                user=user_obj,
                defaults={'company': company},
            )

            return redirect('users')

    return render(request, 'registration/user_edit.html', {
        'user_obj': user_obj,
        'error': error,
        'branches': branches,
        'selected_branch_id': user_branch.branch_id if user_branch else '',
        'selected_role': current_role,
        'company': company,
    })


@login_required
def user_delete(request, user_id):
    if request.user.is_superuser:
        return redirect('home')

    company = get_company(request.user)
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj == request.user:
        return render(request, 'core/user_list.html', {
            'users': _users_with_branch_and_company(company),
            'error': 'Δεν μπορείς να διαγράψεις τον δικό σου λογαριασμό.',
            'company': company,
        })

    user_obj.delete()
    return redirect('users')


@login_required
def company_onboarding(request):
    if not request.user.is_superuser:
        return redirect('home')

    error = None
    success = None

    if request.method == 'POST':
        form = CompanyOnboardingForm(request.POST)

        if form.is_valid():
            company_name = form.cleaned_data['company_name'].strip()
            branch_name = form.cleaned_data['branch_name'].strip()
            branch_address = form.cleaned_data['branch_address'].strip()
            branch_latitude = form.cleaned_data['branch_latitude']
            branch_longitude = form.cleaned_data['branch_longitude']
            admin_username = form.cleaned_data['admin_username'].strip()
            admin_password = form.cleaned_data['admin_password']
            default_category_name = form.cleaned_data['default_category_name'].strip()
            default_unit_name = form.cleaned_data['default_unit_name'].strip()
            default_unit_code = form.cleaned_data['default_unit_code'].strip()

            if Company.objects.filter(name=company_name).exists():
                error = 'Υπάρχει ήδη εταιρεία με αυτό το όνομα.'
            elif User.objects.filter(username=admin_username).exists():
                error = 'Υπάρχει ήδη χρήστης με αυτό το username.'
            else:
                with transaction.atomic():
                    company = Company.objects.create(
                        name=company_name,
                        display_name=company_name,
                        active=True,
                    )

                    branch = Branch.objects.create(
                        company=company,
                        name=branch_name,
                        address=branch_address,
                        latitude=branch_latitude,
                        longitude=branch_longitude,
                    )

                    Category.objects.create(company=company, name=default_category_name)
                    Unit.objects.create(company=company, name=default_unit_name, code=default_unit_code)

                    user = User.objects.create_user(
                        username=admin_username,
                        password=admin_password,
                    )
                    user.is_active = True
                    user.is_staff = True
                    user.is_superuser = False
                    user.save()

                    admin_group, _ = Group.objects.get_or_create(name='admin')
                    user.groups.add(admin_group)

                    UserCompany.objects.create(user=user, company=company)
                    UserBranch.objects.create(user=user, branch=branch)
                    UserProfile.objects.update_or_create(
                        user=user,
                        defaults={'must_change_password': True},
                    )

                success = f'Η εταιρεία "{company_name}" δημιουργήθηκε επιτυχώς με admin "{admin_username}".'
                form = CompanyOnboardingForm()
        else:
            error = 'Υπάρχουν μη έγκυρα πεδία στη φόρμα.'
    else:
        form = CompanyOnboardingForm()

    return render(request, 'core/company_onboarding.html', {
        'form': form,
        'error': error,
        'success': success,
    })


@login_required
def platform_companies(request):
    if not request.user.is_superuser:
        return redirect('home')

    companies = Company.objects.all().order_by('name')

    company_rows = []
    for company in companies:
        company_rows.append({
            'company': company,
            'users_count': User.objects.filter(user_company__company=company).distinct().count(),
            'branches_count': Branch.objects.filter(company=company).count(),
            'orders_count': InternalOrder.objects.filter(company=company).count(),
            'drivers_count': User.objects.filter(
                user_company__company=company,
                groups__name='driver'
            ).distinct().count(),
            'admins': User.objects.filter(
                user_company__company=company,
                groups__name='admin'
            ).distinct(),
        })

    return render(request, 'core/platform_companies.html', {
        'company_rows': company_rows,
        'total_companies': companies.count(),
        'active_companies': companies.filter(active=True).count(),
        'inactive_companies': companies.filter(active=False).count(),
        'total_platform_orders': InternalOrder.objects.count(),
    })


@login_required
def platform_company_detail(request, company_id):
    if not request.user.is_superuser:
        return redirect('home')

    company = get_object_or_404(Company, id=company_id)

    users = User.objects.filter(
        user_company__company=company
    ).select_related(
        'user_branch__branch',
        'user_company__company',
        'profile',
    ).prefetch_related('groups').distinct().order_by('username')

    for user in users:
        user.assigned_branch = getattr(getattr(user, 'user_branch', None), 'branch', None)
        user.role_names = ', '.join(group.name for group in user.groups.all())
        user.must_change_password_value = getattr(getattr(user, 'profile', None), 'must_change_password', False)

    branches = Branch.objects.filter(company=company).order_by('name')
    recent_orders = InternalOrder.objects.filter(company=company).select_related(
        'source_branch',
        'destination_branch',
        'assigned_driver',
        'created_by',
    ).order_by('-created_at')[:10]

    admin_users = User.objects.filter(
        user_company__company=company,
        groups__name='admin'
    ).distinct().order_by('username')

    portal_url = request.build_absolute_uri('/login/')

    email_message = f"""Καλησπέρα σας,

Το εταιρικό σας portal είναι έτοιμο.

Σύνδεσμος πλατφόρμας:
{portal_url}

Στοιχεία πρόσβασης διαχειριστή:
Username: {admin_users.first().username if admin_users.exists() else '—'}
Password: [ο προσωρινός κωδικός που έχει οριστεί]

Σημαντικό:
Με την πρώτη είσοδο θα σας ζητηθεί να αλλάξετε τον προσωρινό κωδικό ασφαλείας.

Με εκτίμηση,
Luminex Orders
"""

    return render(request, 'core/platform_company_detail.html', {
        'company': company,
        'users': users,
        'branches': branches,
        'recent_orders': recent_orders,
        'total_orders': InternalOrder.objects.filter(company=company).count(),
        'total_users': User.objects.filter(user_company__company=company).distinct().count(),
        'total_drivers': User.objects.filter(
            user_company__company=company,
            groups__name='driver'
        ).distinct().count(),
        'total_branches': Branch.objects.filter(company=company).count(),
        'admin_users': admin_users,
        'portal_url': portal_url,
        'email_message': email_message,
    })


@login_required
def toggle_company_active(request, company_id):
    if not request.user.is_superuser:
        return redirect('home')

    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        company.active = not company.active
        company.save()

        users = User.objects.filter(user_company__company=company).distinct()
        for user in users:
            if not user.is_superuser:
                user.is_active = company.active
                user.save(update_fields=['is_active'])

    return redirect('platform_companies')


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    if notification.url:
        return redirect(notification.url)

    return redirect('home')


def custom_403(request, exception):
    return render(request, 'errors/403.html', status=403)


def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    return render(request, 'errors/500.html', status=500)