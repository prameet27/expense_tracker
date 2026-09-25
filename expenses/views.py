import calendar
import json
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .forms import ExpenseForm, ReminderForm, EmailUpdateForm, EmailRecipientForm
from .models import Expenses, Notification, Reminder, EmailRecipient
from .notifications import notify_other_users
from .classification import LEVEL_COLORS, CATEGORY_COLORS, classify_level
from .nepali_date import to_bs_string, bs_month_range_label
from .translator import translate_text
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.conf import settings
# Create your views here.

MONTH_CHOICES=[
    (1, "Janauary"), (2, "Febraury"), (3, "March"), (4, "April"), (5, "May"), (6, "June"),
    (7, "July"), (8, "August"), (9, "September"), (10, "October"), (11, "November"), (12, "December"),
]
    
@login_required
def expense_list(request):
    all_expenses = Expenses.objects.all()

    selected_month = request.GET.get("month") or ""
    selected_year = request.GET.get("year") or ""
    expenses = all_expenses

    if selected_month:
        expenses = expenses.filter(date__month = selected_month)
    if selected_year: 
        expenses = expenses.filter(date__year = selected_year)

    expenses = expenses.order_by("-date")
    total = sum(expense.amount for expense in expenses)

    try:
        selected_month_int = int(selected_month) if selected_month else None
    except ValueError:
        selected_month_int = None

    try:
        selected_year_int = int(selected_year) if selected_year else None
    except ValueError:
        selected_year_int = None

    years = sorted(
        {d.year for d in all_expenses.dates('date', 'year')},
        reverse=True
    )

    monthly_summary = (
        all_expenses
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('-month')
    )

    return render(request, 'expenses/list.html', {
        "expenses":expenses,
        "total": total,
        "months": MONTH_CHOICES,
        "years": years,
        "selected_month":selected_month_int,
        "selected_year": selected_year_int,
        "monthly_summary": monthly_summary,
    })


@login_required
def expense_calendar(request):
    today = date.today()

    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month

    if month < 1:
        month, year = 12, year - 1
    elif month > 12:
        month, year = 1, year + 1

    user_expenses = Expenses.objects.all()
    month_expenses = user_expenses.filter(date__year=year, date__month=month)

    day_data = {}
    for expense in month_expenses:
        entry = day_data.setdefault(expense.date.day, {"total": 0, "items": []})
        entry["total"] += expense.amount
        entry["items"].append(expense)

    month_total = sum(entry["total"] for entry in day_data.values())

    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_cells = []
        for day in week:
            if day == 0:
                week_cells.append(None)
            else:
                info = day_data.get(day, {"total": 0, "items": []})
                week_cells.append({
                    "day": day,
                    "total": info["total"],
                    "items": info["items"],
                    "is_today": (year, month, day) == (today.year, today.month, today.day),
                    "bs_label": to_bs_string(date(year, month, day), "%d %B"),
                })
        weeks.append(week_cells)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    years = sorted({d.year for d in user_expenses.dates('date', 'year')}, reverse=True)
    if year not in years:
        years = sorted(years + [year], reverse=True)

    return render(request, "expenses/calendar.html", {
        "weeks": weeks,
        "month": month,
        "year": year,
        "month_name": calendar.month_name[month],
        "months": MONTH_CHOICES,
        "years": years,
        "month_total": month_total,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
    })

@login_required
def expense_summary(request):
    today = date.today()
    user_expenses = Expenses.objects.all()
    years = sorted({d.year for d in user_expenses.dates('date', 'year')}, reverse=True)
    if today.year not in years:
        years = sorted(years + [today.year], reverse=True)

    try:
        selected_year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        selected_year = today.year

    month_param = request.GET.get("month", str(today.month))
    selected_month = None

    if month_param not in ("", "all", "All"):
        try:
            selected_month = int(month_param)
        except ValueError:
            selected_month = None

    all_time_monthly = (
        user_expenses
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
    )

    all_totals_sorted = sorted(float(entry['total']) for entry in all_time_monthly if entry['total'])
    avg_monthly = (sum(all_totals_sorted) / len(all_totals_sorted)) if all_totals_sorted else None

    year_expenses = user_expenses.filter(date__year = selected_year)

    if selected_month:
        month_expenses = year_expenses.filter(date__month = selected_month)
        month_total = float(month_expenses.aggregate(total=Sum('amount'))['total'] or 0)
        #month_total = sum(expose.amount for expose in month_expenses)
        level = classify_level(month_total, all_totals_sorted) if all_totals_sorted else None

        category_qs = month_expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
        pie_labels = [c['category'] for c in category_qs]
        pie_values = [float(c['total']) for c in category_qs]

        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
        daily_totals = [0.0] * days_in_month
        for e in month_expenses:
            daily_totals[e.date.day - 1] += float(e.amount)

        bar_labels = [str(d) for d in range(1, days_in_month + 1)]
        bar_values = daily_totals
        bar_colors = [LEVEL_COLORS["medium"]] * days_in_month
        bar_view = "daily"
        period_label = f"{calendar.month_name[selected_month]} {selected_year}"
        bs_period_label = bs_month_range_label(
            date(selected_year, selected_month, 1),
            date(selected_year, selected_month, days_in_month),
        )
    else:
        month_totals = {m:0.0 for m in range(1, 13)}
        for row in year_expenses.annotate(month = TruncMonth('date')).values('month').annotate(total=Sum('amount')):
            month_totals[row['month'].month] = float(row['total'])

        bar_labels = [calendar.month_abbr[m] for m in range(1, 13)]
        bar_values = list(month_totals.values())
        bar_colors = []
        for v in bar_values:
            if v <= 0:
                bar_colors.append("#bdc3c7")
            elif all_totals_sorted:
                bar_colors.append(LEVEL_COLORS[classify_level(v, all_totals_sorted)])
            else:
                bar_colors.append(LEVEL_COLORS["medium"])

        month_total = float(year_expenses.aggregate(total=Sum('amount'))['total'] or 0)
        months_with_data = sum(1 for v in bar_values if v > 0)
        year_avg_monthly = (month_total / months_with_data) if months_with_data > 0 else None
        level = classify_level(month_total, all_totals_sorted) if all_totals_sorted and months_with_data > 0 else None

        category_qs = year_expenses.values('category').annotate(total = Sum('amount')).order_by('-total')
        pie_labels = [c['category'] for c in category_qs]
        pie_values = [float(c['total']) for c in category_qs]
        bar_view = "monthly"
        period_label = str(selected_year)
        bs_period_label = bs_month_range_label(
            date(selected_year, 1, 1),
            date(selected_year, 12, 31),
        )

    pie_colors = [CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i in range(len(pie_labels))]

    return render(request, "expenses/summary.html", {
        "years": years,
        "months": MONTH_CHOICES,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "period_label": period_label,
        "bs_period_label": bs_period_label,
        "month_total": month_total,
        "level": level,
        "level_color":LEVEL_COLORS.get(level, "#7f8c8d"),
        "avg_monthly": avg_monthly,
        "bar_view": bar_view,
        "has_pie_data": bool(pie_values),
        "has_bar_data": any(bar_values),
        "pie_labels_json": json.dumps(pie_labels),
        "pie_values_json":json.dumps(pie_values),
        "pie_colors_json": json.dumps(pie_colors),
        "bar_labels_json": json.dumps(bar_labels),
        "bar_values_json": json.dumps(bar_values),
        "bar_colors_json": json.dumps(bar_colors)
    })

@login_required
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            notify_other_users(request.user, "created", expense)
            return redirect(
                "expense_list"
            )
    else:
        form = ExpenseForm()

    return render(request, "expenses/add.html", {
        "form": form
    })


@login_required
def edit_expense(request, id):
    expense = get_object_or_404(Expenses, id=id, user=request.user)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            notify_other_users(request.user, "updated", expense)
            return redirect("expense_list")
    else:
        form = ExpenseForm(instance=expense)
    return render(request, "expenses/edit.html",{
        "form": form,
        "expense": expense
    } )

@login_required
def delete_expense(request, id):
    expense = get_object_or_404(Expenses, id=id, user = request.user)
    if request.method == "POST":
        notify_other_users(request.user, "deleted", expense)
        expense.delete()
        return redirect("expense_list")

    return render(request, "expenses/delete.html",
                      {
                          "expense": expense
                      })


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(recipient = request.user)

    notifications.filter(is_read=False).update(is_read=True)
    return render(request, "expenses/notifications.html", {
        "notifications": notifications
    })


@login_required
def mark_all_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(recipient= request.user, is_read=False).update(is_read=True)
    return redirect("notifications_list")


@login_required
def translate_text_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    text = request.POST.get("text", "")
    direction = request.POST.get("direction", "en_to_ne")
    source, target = ("ne", "en") if direction == "ne_to_en" else ("en", "ne")

    translated, error = translate_text(text, source, target)
    if error:
        return JsonResponse({"error": error}, status=502)

    return JsonResponse({"translated": translated})


@login_required
def reminders_list(request):
    reminders = list(Reminder.objects.all())
    today = date.today()
    reminders.sort(key=lambda r: r.next_occurrence(today))
    for r in reminders:
        r.next_date = r.next_occurrence(today)
        r.days_until = (r.next_date - today).days
        r.due_slots = r.due_slots_today(today)  # non-empty -> auto-open the compose dialog
        r.default_subject = r.default_wish_subject()
        r.default_message = r.default_wish_message(today)

    return render(request, "expenses/reminders.html", {
        "reminders": reminders,
    })


@login_required
def add_reminder(request):
    if request.method == "POST":
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.created_by = request.user
            reminder.save()
            return redirect("reminders_list")
    else:
        form = ReminderForm()

    return render(request, "expenses/add_reminder.html", {
        "form": form,
    })


@login_required
def edit_reminder(request, id):
    reminder = get_object_or_404(Reminder, id=id, created_by=request.user)
    if request.method == "POST":
        form = ReminderForm(request.POST, instance=reminder)
        if form.is_valid():
            form.save()
            return redirect("reminders_list")
    else:
        form = ReminderForm(instance=reminder)

    return render(request, "expenses/edit_reminder.html", {
        "form": form,
        "reminder": reminder,
    })


@login_required
def delete_reminder(request, id):
    reminder = get_object_or_404(Reminder, id=id, created_by=request.user)
    if request.method == "POST":
        reminder.delete()
        return redirect("reminders_list")

    return render(request, "expenses/delete_reminder.html", {
        "reminder": reminder,
    })


@login_required
def send_wish(request, id):
    """
    "Compose new mail"-style sender: lets the logged-in user send a wish
    email for a reminder right now, to any address - a registered app
    user or a random outside email. Also reachable any time (not just on
    the reminder's due date) via the "Send Wish" button on the list page.
    """
    reminder = get_object_or_404(Reminder, id=id)

    if request.method == "POST":
        to_email = (request.POST.get("to_email") or "").strip()
        subject = (request.POST.get("subject") or "").strip() or reminder.default_wish_subject()
        message = (request.POST.get("message") or "").strip()

        if not to_email:
            messages.error(request, "Please enter a recipient email address.")
            return redirect("reminders_list")

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            reply_to=[request.user.email] if request.user.email else None,
        )
        email.send(fail_silently=False)

        # If the recipient happens to be a registered app user, also notify
        # them inside the app, exactly like the automatic reminder system does.
        matched_user = User.objects.filter(email__iexact=to_email).first()
        if matched_user:
            Notification.objects.create(
                recipient=matched_user,
                actor=request.user,
                verb="reminder",
                expense_title=f"{request.user.get_full_name() or request.user.username} sent a wish: {subject}",
                amount=0,
            )

        messages.success(request, f"Wish email sent to {to_email}.")
        return redirect("reminders_list")

    # GET: nothing to render standalone - the compose form lives inline as a
    # <dialog> on the reminders list page.
    return redirect("reminders_list")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = EmailUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = EmailUpdateForm(instance=request.user)

    return render(request, "expenses/profile.html", {
        "form": form,
    })

@login_required
def email_list(request):
    recipients = EmailRecipient.objects.filter(added_by=request.user)
    if request.method == "POST":
        form = EmailRecipientForm(request.POST)
        if form.is_valid():
            recipient = form.save(commit=False)
            recipient.added_by = request.user
            recipient.save()
            return redirect("email_list")
    else:
        form = EmailRecipientForm()
    return render(request, "expenses/email_list.html", {
        "recipients": recipients,
        "form": form,
    })


@login_required
def delete_email_recipient(request, id):
    recipient = get_object_or_404(
        EmailRecipient, id=id, added_by=request.user
    )
    if request.method == "POST":
        recipient.delete()
    return redirect("email_list")
