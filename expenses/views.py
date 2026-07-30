from django.shortcuts import render, redirect, get_object_or_404
from .forms import ExpenseForm
from .models import Expenses
from django.contrib.auth.decorators import login_required
# Create your views here.

@login_required
def expense_list(request):
    expenses = Expenses.objects.filter(user=request.user)
    total = sum(expense.amount for expense in expenses)
    return render(request, 'expenses/list.html', {
        "expenses":expenses,
        "total": total
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
