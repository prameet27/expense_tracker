import calendar
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ExpenseForm
from .models import Expenses
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
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
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
        expense.delete()
        return redirect("expense_list")

    return render(request, "expenses/delete.html",
                      {
                          "expense": expense
                      })
