from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from core.decorators import admin_required
from core.models import UserCompany
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import io

from .forms import IncomeExpenseForm, InvoiceForm
from .models import IncomeExpense, Invoice


def get_company(user):
    uc = UserCompany.objects.filter(user=user).select_related('company').first()
    return uc.company if uc else None


# =====================
# INVOICES (ALL USERS)
# =====================

@login_required
def invoice_list(request):
    company = get_company(request.user)

    invoices = Invoice.objects.filter(company=company)

    status = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()

    if search:
        invoices = invoices.filter(company=company).filter(
            invoice_number__icontains=search
        ) | Invoice.objects.filter(
            company=company,
            partner_name__icontains=search
        )

    invoices = invoices.order_by('-issue_date', '-created_at')

    if status == 'pending':
        invoices = [inv for inv in invoices if inv.computed_status == 'pending']
    elif status == 'paid':
        invoices = [inv for inv in invoices if inv.computed_status == 'paid']
    elif status == 'overdue':
        invoices = [inv for inv in invoices if inv.computed_status == 'overdue']
    else:
        invoices = list(invoices)

    total_amount = sum(inv.amount for inv in invoices) if invoices else 0
    pending_count = sum(1 for inv in invoices if inv.computed_status == 'pending')
    paid_count = sum(1 for inv in invoices if inv.computed_status == 'paid')
    overdue_count = sum(1 for inv in invoices if inv.computed_status == 'overdue')

    return render(request, 'finance/invoice_list.html', {
        'invoices': invoices,
        'selected_status': status,
        'search_query': search,
        'total_amount': total_amount,
        'pending_count': pending_count,
        'paid_count': paid_count,
        'overdue_count': overdue_count,
    })

@login_required
def invoice_create(request):
    company = get_company(request.user)

    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = company
            obj.created_by = request.user
            obj.save()
            return redirect('invoice_list')
    else:
        form = InvoiceForm()

    return render(request, 'finance/invoice_form.html', {
        'form': form,
    })


# =====================
# INCOME / EXPENSE (ADMIN ONLY)
# =====================

@admin_required
def income_expense_list(request):
    company = get_company(request.user)

    entries = IncomeExpense.objects.filter(company=company)

    entry_type = request.GET.get('type', '').strip()
    category = request.GET.get('category', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if entry_type:
        entries = entries.filter(type=entry_type)

    if category:
        entries = entries.filter(category__icontains=category)

    if date_from:
        entries = entries.filter(date__gte=date_from)

    if date_to:
        entries = entries.filter(date__lte=date_to)

    summary_entries = entries
    entries = entries.order_by('-date', '-created_at')

    total_income = summary_entries.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = summary_entries.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
    net_total = total_income - total_expense

    return render(request, 'finance/income_expense_list.html', {
        'entries': entries,
        'selected_type': entry_type,
        'selected_category': category,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_total': net_total,
    })

@admin_required
def income_expense_create(request):
    company = get_company(request.user)

    if request.method == 'POST':
        form = IncomeExpenseForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = company
            obj.created_by = request.user
            obj.save()
            return redirect('income_expense_list')
    else:
        form = IncomeExpenseForm()

    return render(request, 'finance/income_expense_form.html', {
        'form': form,
    })


# =====================
# FINANCE DASHBOARD (ADMIN ONLY)
# =====================

@admin_required
def finance_dashboard(request):
    company = get_company(request.user)

    today = date.today()

    entries = IncomeExpense.objects.filter(company=company)

    today_entries = entries.filter(date=today)

    month_entries = entries.filter(date__month=today.month, date__year=today.year)

    year_entries = entries.filter(date__year=today.year)

    def calc(qs):
        income = qs.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense = qs.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        return income, expense, income - expense

    today_income, today_expense, today_net = calc(today_entries)
    month_income, month_expense, month_net = calc(month_entries)
    year_income, year_expense, year_net = calc(year_entries)

    return render(request, 'finance/dashboard.html', {
        'today_income': today_income,
        'today_expense': today_expense,
        'today_net': today_net,

        'month_income': month_income,
        'month_expense': month_expense,
        'month_net': month_net,

        'year_income': year_income,
        'year_expense': year_expense,
        'year_net': year_net,
    })
from django.shortcuts import get_object_or_404


# =====================
# INVOICE EDIT / DELETE
# =====================

@login_required
def invoice_edit(request, invoice_id):
    company = get_company(request.user)

    invoice = get_object_or_404(Invoice, id=invoice_id, company=company)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            return redirect('invoice_list')
    else:
        form = InvoiceForm(instance=invoice)

    return render(request, 'finance/invoice_form.html', {
        'form': form,
    })


@login_required
def invoice_delete(request, invoice_id):
    company = get_company(request.user)

    invoice = get_object_or_404(Invoice, id=invoice_id, company=company)

    invoice.delete()
    return redirect('invoice_list')


# =====================
# INCOME / EXPENSE EDIT / DELETE
# =====================

@admin_required
def income_expense_edit(request, entry_id):
    company = get_company(request.user)

    entry = get_object_or_404(IncomeExpense, id=entry_id, company=company)

    if request.method == 'POST':
        form = IncomeExpenseForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('income_expense_list')
    else:
        form = IncomeExpenseForm(instance=entry)

    return render(request, 'finance/income_expense_form.html', {
        'form': form,
    })


@admin_required
def income_expense_delete(request, entry_id):
    company = get_company(request.user)

    entry = get_object_or_404(IncomeExpense, id=entry_id, company=company)

    entry.delete()
    return redirect('income_expense_list')

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
import io


@login_required
def export_financial_pdf(request):
    company = get_company(request.user)

    if not company:
        return HttpResponse("No company", status=400)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    entries = IncomeExpense.objects.filter(company=company)

    total_income = sum(e.amount for e in entries if e.type == 'income')
    total_expense = sum(e.amount for e in entries if e.type == 'expense')

    elements.append(Paragraph("Financial Report", styles['Title']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Total Income: {total_income} €", styles['Normal']))
    elements.append(Paragraph(f"Total Expense: {total_expense} €", styles['Normal']))
    elements.append(Paragraph(f"Net Profit: {total_income - total_expense} €", styles['Normal']))

    doc.build(elements)

    buffer.seek(0)

    return HttpResponse(buffer, content_type='application/pdf')

@admin_required
def export_financial_pdf(request):
    company = get_company(request.user)

    if not company:
        return HttpResponse("No company found.", status=400)

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    entries = IncomeExpense.objects.filter(company=company)
    invoices = Invoice.objects.filter(company=company)

    if date_from:
        entries = entries.filter(date__gte=date_from)
        invoices = invoices.filter(issue_date__gte=date_from)

    if date_to:
        entries = entries.filter(date__lte=date_to)
        invoices = invoices.filter(issue_date__lte=date_to)

    total_income = entries.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = entries.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
    net_total = total_income - total_expense

    pending_count = sum(1 for inv in invoices if inv.computed_status == 'pending')
    paid_count = sum(1 for inv in invoices if inv.computed_status == 'paid')
    overdue_count = sum(1 for inv in invoices if inv.computed_status == 'overdue')
    invoice_total_amount = sum(inv.amount for inv in invoices) if invoices else 0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title = f"Financial Report - {company.display_name or company.name}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    period_text = f"Περίοδος: {date_from or 'Αρχή'} έως {date_to or 'Σήμερα'}"
    elements.append(Paragraph(period_text, styles['Normal']))
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Σύνοψη Εσόδων / Εξόδων", styles['Heading2']))
    elements.append(Spacer(1, 8))

    finance_data = [
        ['Πεδίο', 'Ποσό'],
        ['Σύνολο Εσόδων', f'{total_income} €'],
        ['Σύνολο Εξόδων', f'{total_expense} €'],
        ['Καθαρό Αποτέλεσμα', f'{net_total} €'],
    ]

    finance_table = Table(finance_data, colWidths=[250, 200])
    finance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(finance_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Σύνοψη Τιμολογίων", styles['Heading2']))
    elements.append(Spacer(1, 8))

    invoice_data = [
        ['Πεδίο', 'Τιμή'],
        ['Συνολικό Ποσό Τιμολογίων', f'{invoice_total_amount} €'],
        ['Εκκρεμή', str(pending_count)],
        ['Πληρωμένα', str(paid_count)],
        ['Ληξιπρόθεσμα', str(overdue_count)],
    ]

    invoice_table = Table(invoice_data, colWidths=[250, 200])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(invoice_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Το report δημιουργήθηκε αυτόματα από το Luminex Orders.", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="financial_report.pdf"'
    return response