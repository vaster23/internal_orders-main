from django.contrib.auth.models import User

from .models import AuditLog, Notification, UserCompany


def get_user_company(user):
    if not user or not user.is_authenticated:
        return None

    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    return user_company.company if user_company else None


def create_audit_log(*, user=None, company=None, action='', target_type='', target_id='', description=''):
    if company is None and user is not None and getattr(user, 'is_authenticated', False):
        company = get_user_company(user)

    AuditLog.objects.create(
        company=company,
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id or ''),
        description=description,
    )


def create_notification(*, user, company=None, title='', message='', url=''):
    if company is None:
        company = get_user_company(user)

    if not company:
        return

    Notification.objects.create(
        company=company,
        user=user,
        title=title,
        message=message,
        url=url,
    )


def create_company_notification_for_admins(*, company, title='', message='', url=''):
    admin_users = User.objects.filter(
        user_company__company=company,
        groups__name='admin',
        is_active=True,
    ).distinct()

    for user in admin_users:
        create_notification(
            user=user,
            company=company,
            title=title,
            message=message,
            url=url,
        )


def create_company_notification_for_drivers(*, company, title='', message='', url=''):
    driver_users = User.objects.filter(
        user_company__company=company,
        groups__name='driver',
        is_active=True,
    ).distinct()

    for user in driver_users:
        create_notification(
            user=user,
            company=company,
            title=title,
            message=message,
            url=url,
        )

        from core.models import UserCompany


def get_company(user):
    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    return user_company.company if user_company else None