from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Expenses(models.Model):
    CATEGORY_CHOICES=[
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Health', 'Health'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    date = models.DateField()
    description = models.TextField(blank=True)
    def __str__(self):
        self.title

class Notification(models.Model):
    VERB_CHOICES = [
        ('created', 'created'),
        ('updated', 'updated'),
        ('deleted', 'deleted'),
        ('summary', 'monthly summary'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="actions")

    verb = models.CharField(max_length=20, choices=VERB_CHOICES)
    expense_title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    level = models.CharField(max_length=10, blank=True)

    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)

    pdf_file = models.FileField(upload_to="monthly_reports/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "Someone"
        return f"{actor_name} {self.verb} '{self.expense_title}'"


class MonthlySummaryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'year', 'month')

    def __str__(self):
        return f"{self.user.username} summary for {self.month}/{self.year}"