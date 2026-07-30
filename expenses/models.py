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