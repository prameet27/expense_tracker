from django.contrib import admin
from .models import Expenses, Notification
# Register your models here.
admin.site.register(Expenses)
admin.site.register(Notification)