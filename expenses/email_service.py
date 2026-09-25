import calendar
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .classification import classify_level
from .models import Expenses, EmailRecipient, Reminder, ReminderLog
from .pdf_reports import build_monthly_report_pdf


def send_due_reminder_emails(today=None):
    """
    Send birthday/anniversary emails whose configured reminder date (reminder 1
    and/or reminder 2) is today. Each due reminder is emailed to:
      - the person being wished (the reminder's own `email` field), and
      - every active address on the Monthly Report email list.
    """
    today = today or timezone.localdate()
    sent = 0

    mailing_list = list(
        EmailRecipient.objects.filter(is_active=True).values_list("email", flat=True)
    )

    for reminder in Reminder.objects.select_related("created_by"):
        for slot, days_before, reminder_date in reminder.reminder_dates(today):
            if reminder_date != today:
                continue

            occurrence_year = reminder.next_occurrence(today).year
            if ReminderLog.objects.filter(
                reminder=reminder, year=occurrence_year, slot=slot
            ).exists():
                continue

            recipients = list(mailing_list)
            if reminder.email:
                recipients.append(reminder.email)
            if reminder.created_by.email:
                recipients.append(reminder.created_by.email)
            # De-duplicate while preserving order.
            recipients = list(dict.fromkeys(recipients))
            if not recipients:
                continue

            occurrence = reminder.next_occurrence(today)
            kind = reminder.get_reminder_type_display()
            days_text = "today" if days_before == 0 else f"in {days_before} days"
            slot_label = "Reminder 1" if slot == "r1" else "Reminder 2"

            subject = f"{kind} Reminder ({slot_label}): {reminder.person_name}"
            message = (
                f"Hello,\n\n"
                f"This is an automatic {kind.lower()} reminder for {reminder.person_name}.\n"
                f"The date is {occurrence.strftime('%B %d, %Y')} ({days_text}).\n"
            )
            if reminder.notes:
                message += f"\nNotes: {reminder.notes}\n"
            message += "\n— Expense Tracker"

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
            ReminderLog.objects.create(reminder=reminder, year=occurrence_year, slot=slot)
            sent += 1

    return sent


def send_monthly_expense_report(year, month):
    """Generate one household PDF and email it to every active list address."""
    recipients = list(
        EmailRecipient.objects.filter(is_active=True)
        .values_list("email", flat=True)
    )
    if not recipients:
        return 0

    expenses = list(
        Expenses.objects.filter(date__year=year, date__month=month)
        .select_related("user")
        .order_by("date", "id")
    )
    total = float(
        Expenses.objects.filter(date__year=year, date__month=month)
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    # Use the same spending-level classification used by the summary screen.
    monthly_totals = []
    for row in (
        Expenses.objects
        .annotate(month_key=TruncMonth("date"))
        .values("month_key")
        .annotate(total=Sum("amount"))
    ):
        if row["total"]:
            monthly_totals.append(float(row["total"]))

    level = classify_level(total, sorted(monthly_totals)) if monthly_totals else None
    pdf = build_monthly_report_pdf(year, month, expenses, total, level)

    subject = f"Monthly Expense Report - {calendar.month_name[month]} {year}"
    body = (
        f"Hello,\n\n"
        f"Attached is the household expense report for "
        f"{calendar.month_name[month]} {year}.\n\n"
        f"Total expenses: ${total:,.2f}\n\n"
        f"— Expense Tracker"
    )

    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
    )
    email.attach(pdf.name, pdf.read(), "application/pdf")
    email.send(fail_silently=False)
    return len(recipients)
