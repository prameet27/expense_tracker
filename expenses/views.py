import calendar
import json
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ExpenseForm
from .models import Expenses, Notification
from .notifications import notify_other_users
from .classification import LEVEL_COLORS, CATEGORY_COLORS, classify_level
from .nepali_date import to_bs_string, bs_month_range_label
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required
# Create your views here.

MONTH_CHOICES=[
    (1, "Janauary"), (2, "Febraury"), (3, "March"), (4, "April"), (5, "May"), (6, "June"),
    (7, "July"), (8, "August"), (9, "September"), (10, "October"), (11, "November"), (12, "December"),
]
    
@login_required
def expense_list(request):
    all_expenses = Expenses.objects.filter(user=request.user)

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

    user_expenses = Expenses.objects.filter(user=request.user)
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
    user_expenses = Expenses.objects.filter(user=request.user)
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
        "level_colors":LEVEL_COLORS.get(level, "#7f8c8d"),
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