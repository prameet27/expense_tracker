import calendar
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .models import Notification, MonthlySummaryLog, Expenses
from .classification import classify_level
from .pdf_reports import build_monthly_report_pdf

def notify_other_users(actor, verb, expense):
    others = User.objects.exclude(id=actor.id)
    Notification.objects.bulk_create([
        Notification(
            recipient = user,
            actor=actor,
            verb=verb,
            expense_title = expense.title,
            amount = expense.amount
        )

        for user in others
    ])

def _last_completed_month(today):
    first_of_this_month = today.replace(day=1)
    last_day_prev_month = first_of_this_month - timedelta(days=1)
    return last_day_prev_month.year, last_day_prev_month.month


def check_and_send_monthly_summaries(today=None):
    today = today or date.today()
    year, month = _last_completed_month(today)

    for user in User.objects.all():
        if MonthlySummaryLog.objects.filter(user=user, year=year, month=month).exists():
            continue

        user_expenses = Expenses.objects.filter(user=user)
        month_expenses = user_expenses.filter(date__year = year, date__month = month).order_by('date')
        month_total = float(
            month_expenses.aggregate(total=Sum('amount'))['total'] or 0
        )

        all_time_monthly = (
            user_expenses
            .annotate(m=TruncMonth('date'))
            .values('m')
            .annotate(total=Sum('amount'))
        )

        all_totals_sorted = sorted(float(row['total']) for row in all_time_monthly if row['total'])
        level = classify_level(month_total, all_totals_sorted) if all_totals_sorted else "medium"
        month_name = calendar.month_name[month]

        notification = Notification.objects.create(
            recipient=user,
            actor=None,
            verb="summary",
            expense_title=f"Monthly Summary - {month_name} {year}",
            amount=month_total,
            level=level,
            year=year,
            month=month,
        )

        pdf_content_file = build_monthly_report_pdf(
            user=user, 
            year=year,
            month=month,
            expenses=month_expenses,
            month_total=month_total,
            level=level,
        )

        notification.pdf_file.save(pdf_content_file.name, pdf_content_file, save=True)
        
        MonthlySummaryLog.objects.create(user=user, year=year, month=month)