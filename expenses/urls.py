from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name="expense_list"),
    path('add/', views.add_expense, name="add_expense"),
    path('edit/<int:id>', views.edit_expense, name="edit_expense"),
    path('delete/<int:id>', views.delete_expense, name="delete_expense"),
    path('history/', views.expense_calendar, name="expense_calendar"),
    path('summary/', views.expense_summary, name="expense_summary"),
    path('notifications/', views.notifications_list, name="notifications_list"),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name="mark_all_notifications_read"),
]