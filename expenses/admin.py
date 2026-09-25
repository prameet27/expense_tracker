from django.contrib import admin
from .models import Expenses, Notification, EmailRecipient, Reminder, ReminderLog, MonthlySummaryLog

admin.site.register(Expenses)
admin.site.register(Notification)
admin.site.register(EmailRecipient)
admin.site.register(Reminder)
admin.site.register(ReminderLog)
admin.site.register(MonthlySummaryLog)
