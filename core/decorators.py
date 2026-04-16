from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

from .models import UserCompany


def is_platform_owner(user):
    return user.is_authenticated and user.is_superuser


def is_company_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='admin').exists()
    )


def admin_required(view_func):
    return user_passes_test(is_company_admin)(view_func)


def company_is_active(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    if not user_company:
        return False

    return user_company.company.active


def active_company_required(view_func):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        user_company = UserCompany.objects.filter(user=request.user).select_related('company').first()
        if not user_company or not user_company.company.active:
            return redirect('company_inactive')

        return view_func(request, *args, **kwargs)

    return wrapped