from django.contrib.auth.models import User
from .models import Notification

def notify_other_users(actor, verb, expense):
    others = User.objects.exclude(id=actor.id)
    Notification.objects.bulk_create([
        Notification(
            recipient = user,
            actor=actor,
            verb=verb,
            expense_title = expense.title,
            amount = expense.amount
        )

        for user in others
    ])