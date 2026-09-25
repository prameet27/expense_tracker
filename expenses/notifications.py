import calendar
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .models import Notification, MonthlySummaryLog, Expenses, Reminder, ReminderLog, EmailRecipient
from .classification import classify_level
from .pdf_reports import build_monthly_report_pdf
from .email_utils import send_reminder_email
from django.core.mail import send_mail
from django.conf import settings


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
    """
    Compute ONE combined household total for the most recently completed
    month (across all users' shared expenses), and notify every user with
    the same total/level/PDF. Idempotent via MonthlySummaryLog's unique
    (year, month) constraint - runs at most once per month, regardless of
    who triggers it or how many users there are.
    """
    today = today or date.today()
    year, month = _last_completed_month(today)

    if MonthlySummaryLog.objects.filter(year=year, month=month).exists():
        return

    all_expenses = Expenses.objects.all()
    month_expenses = all_expenses.filter(date__year=year, date__month=month).order_by('date')
    month_total = float(month_expenses.aggregate(total=Sum('amount'))['total'] or 0)

    all_time_monthly = (
        all_expenses
        .annotate(m=TruncMonth('date'))
        .values('m')
        .annotate(total=Sum('amount'))
    )
    all_totals_sorted = sorted(float(row['total']) for row in all_time_monthly if row['total'])
    level = classify_level(month_total, all_totals_sorted) if all_totals_sorted else "medium"
    month_name = calendar.month_name[month]

    pdf_content_file = build_monthly_report_pdf(
        year=year,
        month=month,
        expenses=month_expenses,
        month_total=month_total,
        level=level,
    )

    saved_pdf_name = None
    for user in User.objects.all():
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
        if saved_pdf_name is None:
            # First recipient: actually upload the PDF content to storage.
            notification.pdf_file.save(pdf_content_file.name, pdf_content_file, save=True)
            saved_pdf_name = notification.pdf_file.name
        else:
            # Subsequent recipients: point at the same already-uploaded file.
            notification.pdf_file.name = saved_pdf_name
            notification.save(update_fields=["pdf_file"])

    MonthlySummaryLog.objects.create(year=year, month=month)


def check_and_send_reminders(today=None):
    """
    For every Reminder, check whether today is a "remind on" date - either
    reminder 1 or reminder 2 (original_date's month/day this year, minus the
    configured number of days before). If so, and that slot hasn't already
    been sent for this year, notify every app user in-app, and email:
      - the person being wished (the reminder's own `email` field), and
      - everyone on the Monthly Report email list.
    Idempotent via ReminderLog's unique (reminder, year, slot) constraint.
    """
    today = today or date.today()
    mailing_list = list(
        EmailRecipient.objects.filter(is_active=True).values_list("email", flat=True)
    )

    for reminder in Reminder.objects.all():
        for slot, days_before, remind_on in reminder.reminder_dates(today):
            if remind_on != today:
                continue
            if ReminderLog.objects.filter(reminder=reminder, year=today.year, slot=slot).exists():
                continue

            years_count = today.year - reminder.original_date.year
            when = "today" if days_before == 0 else f"in {days_before} day(s)"
            slot_label = "" if slot == "r1" else " (2nd reminder)"

            if reminder.reminder_type == "birthday":
                message = f"{reminder.person_name}'s birthday is {when}! Turning {years_count}.{slot_label}"
                subject = f"🎂 Birthday Reminder: {reminder.person_name}"
            elif reminder.reminder_type == "anniversary":
                message = f"{reminder.person_name}'s anniversary is {when}! {years_count} year(s).{slot_label}"
                subject = f"💍 Anniversary Reminder: {reminder.person_name}"
            else:
                message = f"Reminder: {reminder.person_name} - {reminder.notes or reminder.get_reminder_type_display()} ({when}){slot_label}"
                subject = f"🔔 Reminder: {reminder.person_name}"

            for user in User.objects.all():
                Notification.objects.create(
                    recipient=user,
                    actor=None,
                    verb="reminder",
                    expense_title=message,
                    amount=0,
                )

            # Email the person being wished directly, plus everyone on the
            # monthly report mailing list.
            recipients = list(mailing_list)
            if reminder.email:
                recipients.append(reminder.email)
            recipients = list(dict.fromkeys(recipients))
            if recipients:
                send_reminder_email(recipients, subject, message)

            ReminderLog.objects.create(reminder=reminder, year=today.year, slot=slot)