from django import forms
from django.contrib.auth.models import User
from .models import Expenses, Reminder, EmailRecipient

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


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = [
            'person_name',
            'email',
            'reminder_type',
            'original_date',
            'reminder1_days_before',
            'reminder2_days_before',
            'notes',
        ]
        widgets = {
            'original_date': forms.DateInput(attrs={'type': 'date'}),
            'email': forms.EmailInput(attrs={'placeholder': 'name@example.com'}),
        }


class EmailUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'required': True}),
        }

class EmailRecipientForm(forms.ModelForm):

    class Meta:
        model = EmailRecipient

        fields = [
            "name",
            "email",
            "is_active",
        ]

        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "name@example.com"
                }
            ),
        }
