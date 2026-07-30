from django import forms
from .models import Expenses

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expenses

        fields = [
            'title',
            'category',
            'amount',
            'date',
            'description'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type':'date'})
        }