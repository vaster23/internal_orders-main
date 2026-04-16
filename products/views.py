from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required
from core.models import UserCompany
from core.utils import create_audit_log

from .models import Branch, Category, Product, Unit


def _get_user_company(user):
    user_company = UserCompany.objects.filter(user=user).select_related('company').first()
    return user_company.company if user_company else None


@admin_required
def product_list(request):
    company = _get_user_company(request.user)

    products = Product.objects.select_related(
        'unit',
        'branch',
        'category',
        'branch__company',
        'unit__company',
        'category__company',
    ).order_by('name')

    if company:
        products = products.filter(
            branch__company=company,
            unit__company=company,
            category__company=company,
        )
    else:
        products = products.none()

    return render(request, 'products/products_list.html', {'products': products})


@admin_required
def product_add(request):
    error = None
    company = _get_user_company(request.user)

    units = Unit.objects.order_by('name')
    categories = Category.objects.order_by('name')
    branches = Branch.objects.order_by('name')

    if company:
        units = units.filter(company=company, active=True)
        categories = categories.filter(company=company, active=True)
        branches = branches.filter(company=company, active=True)
    else:
        units = units.none()
        categories = categories.none()
        branches = branches.none()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit')
        branch_id = request.POST.get('branch')
        category_id = request.POST.get('category')
        active = request.POST.get('active') == 'on'

        if company is None:
            error = 'Ο λογαριασμός δεν έχει συνδεδεμένη εταιρεία.'
        elif not name or not unit_id or not branch_id or not category_id:
            error = 'Όλα τα βασικά πεδία είναι υποχρεωτικά.'
        else:
            unit = get_object_or_404(Unit, id=unit_id, company=company, active=True)
            branch_obj = get_object_or_404(Branch, id=branch_id, company=company, active=True)
            category_obj = get_object_or_404(Category, id=category_id, company=company, active=True)

            product = Product.objects.create(
                name=name,
                description=description,
                unit=unit,
                branch=branch_obj,
                category=category_obj,
                active=active,
            )

            create_audit_log(
                user=request.user,
                company=company,
                action='create_product',
                target_type='Product',
                target_id=product.id,
                description=f'Δημιουργήθηκε προϊόν {product.name}'
            )

            return redirect('products:product_list')

    return render(request, 'products/product_add.html', {
        'error': error,
        'units': units,
        'branches': branches,
        'categories': categories,
    })


@admin_required
def product_edit(request, product_id):
    company = _get_user_company(request.user)

    product = get_object_or_404(
        Product.objects.select_related(
            'branch__company',
            'unit__company',
            'category__company',
        ),
        id=product_id,
    )

    if not company or (
        product.branch.company_id != company.id or
        product.unit.company_id != company.id or
        product.category.company_id != company.id
    ):
        return redirect('products:product_list')

    error = None
    units = Unit.objects.filter(company=company, active=True).order_by('name')
    branches = Branch.objects.filter(company=company, active=True).order_by('name')
    categories = Category.objects.filter(company=company, active=True).order_by('name')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit')
        branch_id = request.POST.get('branch')
        category_id = request.POST.get('category')
        active = request.POST.get('active') == 'on'

        if not name or not unit_id or not branch_id or not category_id:
            error = 'Όλα τα βασικά πεδία είναι υποχρεωτικά.'
        else:
            product.name = name
            product.description = description
            product.unit = get_object_or_404(Unit, id=unit_id, company=company, active=True)
            product.branch = get_object_or_404(Branch, id=branch_id, company=company, active=True)
            product.category = get_object_or_404(Category, id=category_id, company=company, active=True)
            product.active = active
            product.save()

            create_audit_log(
                user=request.user,
                company=company,
                action='update_product',
                target_type='Product',
                target_id=product.id,
                description=f'Ενημερώθηκε προϊόν {product.name}'
            )

            return redirect('products:product_list')

    return render(request, 'products/product_edit.html', {
        'product': product,
        'error': error,
        'units': units,
        'branches': branches,
        'categories': categories,
    })


@admin_required
def product_delete(request, product_id):
    company = _get_user_company(request.user)

    product = get_object_or_404(
        Product.objects.select_related('branch__company'),
        id=product_id,
    )

    if not company or product.branch.company_id != company.id:
        return redirect('products:product_list')

    if request.method == 'POST':
        product.active = False
        product.save(update_fields=['active'])

        create_audit_log(
            user=request.user,
            company=company,
            action='soft_delete_product',
            target_type='Product',
            target_id=product.id,
            description=f'Απενεργοποιήθηκε προϊόν {product.name}'
        )

        return redirect('products:product_list')

    return render(request, 'products/confirm_delete.html', {
        'title': 'Απενεργοποίηση Προϊόντος',
        'message': f'Θέλεις σίγουρα να απενεργοποιήσεις το προϊόν "{product.name}";',
        'cancel_url': 'products:product_list',
    })


@admin_required
def unit_list(request):
    company = _get_user_company(request.user)
    units = Unit.objects.order_by('name')

    if company:
        units = units.filter(company=company)
    else:
        units = units.none()

    return render(request, 'products/unit_list.html', {'units': units})


@admin_required
def unit_add(request):
    error = None
    company = _get_user_company(request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()

        if company is None:
            error = 'Ο λογαριασμός δεν έχει συνδεδεμένη εταιρεία.'
        elif not name or not code:
            error = 'Το όνομα και ο κωδικός είναι υποχρεωτικά.'
        elif Unit.objects.filter(company=company, code=code).exists():
            error = 'Ο κωδικός υπάρχει ήδη στην εταιρεία.'
        else:
            unit = Unit.objects.create(company=company, name=name, code=code)

            create_audit_log(
                user=request.user,
                company=company,
                action='create_unit',
                target_type='Unit',
                target_id=unit.id,
                description=f'Δημιουργήθηκε μονάδα {unit.name}'
            )

            return redirect('products:unit_list')

    return render(request, 'products/unit_add.html', {'error': error})


@admin_required
def unit_edit(request, unit_id):
    company = _get_user_company(request.user)
    unit = get_object_or_404(Unit, id=unit_id)

    if not company or unit.company_id != company.id:
        return redirect('products:unit_list')

    error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()

        if not name or not code:
            error = 'Το όνομα και ο κωδικός είναι υποχρεωτικά.'
        elif Unit.objects.filter(company=company, code=code).exclude(id=unit.id).exists():
            error = 'Ο κωδικός υπάρχει ήδη στην εταιρεία.'
        else:
            unit.name = name
            unit.code = code
            unit.save()

            create_audit_log(
                user=request.user,
                company=company,
                action='update_unit',
                target_type='Unit',
                target_id=unit.id,
                description=f'Ενημερώθηκε μονάδα {unit.name}'
            )

            return redirect('products:unit_list')

    return render(request, 'products/unit_edit.html', {
        'unit': unit,
        'error': error,
    })


@admin_required
def unit_delete(request, unit_id):
    company = _get_user_company(request.user)
    unit = get_object_or_404(Unit, id=unit_id)

    if not company or unit.company_id != company.id:
        return redirect('products:unit_list')

    if request.method == 'POST':
        unit.active = False
        unit.save(update_fields=['active'])

        create_audit_log(
            user=request.user,
            company=company,
            action='soft_delete_unit',
            target_type='Unit',
            target_id=unit.id,
            description=f'Απενεργοποιήθηκε μονάδα {unit.name}'
        )

        return redirect('products:unit_list')

    return render(request, 'products/confirm_delete.html', {
        'title': 'Απενεργοποίηση Μονάδας',
        'message': f'Θέλεις σίγουρα να απενεργοποιήσεις τη μονάδα "{unit.name} ({unit.code})";',
        'cancel_url': 'products:unit_list',
    })


@admin_required
def branch_list(request):
    company = _get_user_company(request.user)
    branches = Branch.objects.select_related('company').order_by('name')

    if company:
        branches = branches.filter(company=company)
    else:
        branches = branches.none()

    return render(request, 'products/branch_list.html', {'branches': branches})


@admin_required
def branch_add(request):
    error = None
    company = _get_user_company(request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()

        if not name:
            error = 'Το όνομα είναι υποχρεωτικό.'
        elif not company:
            error = 'Ο χρήστης δεν έχει συνδεδεμένη εταιρεία.'
        else:
            branch = Branch.objects.create(
                company=company,
                name=name,
                address=address,
                latitude=latitude or None,
                longitude=longitude or None,
            )

            create_audit_log(
                user=request.user,
                company=company,
                action='create_branch',
                target_type='Branch',
                target_id=branch.id,
                description=f'Δημιουργήθηκε υποκατάστημα {branch.name}'
            )

            return redirect('products:branch_list')

    return render(request, 'products/branch_add.html', {'error': error})


@admin_required
def branch_edit(request, branch_id):
    company = _get_user_company(request.user)
    branch = get_object_or_404(Branch.objects.select_related('company'), id=branch_id)

    if not company or branch.company_id != company.id:
        return redirect('products:branch_list')

    error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        longitude = request.POST.get('longitude', '').strip()

        if not name:
            error = 'Το όνομα είναι υποχρεωτικό.'
        else:
            branch.name = name
            branch.address = address
            branch.latitude = latitude or None
            branch.longitude = longitude or None
            branch.save()

            create_audit_log(
                user=request.user,
                company=company,
                action='update_branch',
                target_type='Branch',
                target_id=branch.id,
                description=f'Ενημερώθηκε υποκατάστημα {branch.name}'
            )

            return redirect('products:branch_list')

    return render(request, 'products/branch_edit.html', {
        'branch': branch,
        'error': error,
    })


@admin_required
def branch_delete(request, branch_id):
    company = _get_user_company(request.user)
    branch_obj = get_object_or_404(Branch.objects.select_related('company'), id=branch_id)

    if not company or branch_obj.company_id != company.id:
        return redirect('products:branch_list')

    if request.method == 'POST':
        branch_obj.active = False
        branch_obj.save(update_fields=['active'])

        create_audit_log(
            user=request.user,
            company=company,
            action='soft_delete_branch',
            target_type='Branch',
            target_id=branch_obj.id,
            description=f'Απενεργοποιήθηκε υποκατάστημα {branch_obj.name}'
        )

        return redirect('products:branch_list')

    return render(request, 'products/confirm_delete.html', {
        'title': 'Απενεργοποίηση Υποκαταστήματος',
        'message': f'Θέλεις σίγουρα να απενεργοποιήσεις το υποκατάστημα "{branch_obj.name}";',
        'cancel_url': 'products:branch_list',
    })


@admin_required
def category_list(request):
    company = _get_user_company(request.user)
    categories = Category.objects.order_by('name')

    if company:
        categories = categories.filter(company=company)
    else:
        categories = categories.none()

    return render(request, 'products/category_list.html', {'categories': categories})


@admin_required
def category_add(request):
    error = None
    company = _get_user_company(request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if company is None:
            error = 'Ο λογαριασμός δεν έχει συνδεδεμένη εταιρεία.'
        elif not name:
            error = 'Το όνομα είναι υποχρεωτικό.'
        elif Category.objects.filter(company=company, name=name).exists():
            error = 'Η κατηγορία υπάρχει ήδη στην εταιρεία.'
        else:
            category = Category.objects.create(company=company, name=name)

            create_audit_log(
                user=request.user,
                company=company,
                action='create_category',
                target_type='Category',
                target_id=category.id,
                description=f'Δημιουργήθηκε κατηγορία {category.name}'
            )

            return redirect('products:category_list')

    return render(request, 'products/category_add.html', {'error': error})


@admin_required
def category_edit(request, category_id):
    company = _get_user_company(request.user)
    category = get_object_or_404(Category, id=category_id)

    if not company or category.company_id != company.id:
        return redirect('products:category_list')

    error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if not name:
            error = 'Το όνομα είναι υποχρεωτικό.'
        elif Category.objects.filter(company=company, name=name).exclude(id=category.id).exists():
            error = 'Η κατηγορία υπάρχει ήδη στην εταιρεία.'
        else:
            category.name = name
            category.save()

            create_audit_log(
                user=request.user,
                company=company,
                action='update_category',
                target_type='Category',
                target_id=category.id,
                description=f'Ενημερώθηκε κατηγορία {category.name}'
            )

            return redirect('products:category_list')

    return render(request, 'products/category_edit.html', {
        'category': category,
        'error': error,
    })


@admin_required
def category_delete(request, category_id):
    company = _get_user_company(request.user)
    category = get_object_or_404(Category, id=category_id)

    if not company or category.company_id != company.id:
        return redirect('products:category_list')

    if request.method == 'POST':
        category.active = False
        category.save(update_fields=['active'])

        create_audit_log(
            user=request.user,
            company=company,
            action='soft_delete_category',
            target_type='Category',
            target_id=category.id,
            description=f'Απενεργοποιήθηκε κατηγορία {category.name}'
        )

        return redirect('products:category_list')

    return render(request, 'products/confirm_delete.html', {
        'title': 'Απενεργοποίηση Κατηγορίας',
        'message': f'Θέλεις σίγουρα να απενεργοποιήσεις την κατηγορία "{category.name}";',
        'cancel_url': 'products:category_list',
    })