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
    path('translate/', views.translate_text_view, name="translate_text"),
    path('reminders/', views.reminders_list, name="reminders_list"),
    path('reminders/add/', views.add_reminder, name="add_reminder"),
    path('reminders/edit/<int:id>', views.edit_reminder, name="edit_reminder"),
    path('reminders/delete/<int:id>', views.delete_reminder, name="delete_reminder"),
    path('reminders/<int:id>/send-wish/', views.send_wish, name="send_wish"),
    path('profile/', views.profile_view, name="profile"),
    path('email-list/', views.email_list, name="email_list"),
    path('email-list/delete/<int:id>', views.delete_email_recipient, name="delete_email_recipient"),
]