from django.core.management.base import BaseCommand
from expenses.email_service import send_due_reminder_emails

class Command(BaseCommand):
    help = "Send due birthday, anniversary and other reminder emails."

    def handle(self, *args, **options):
        count = send_due_reminder_emails()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} reminder email(s)."))