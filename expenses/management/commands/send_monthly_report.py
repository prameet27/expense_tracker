from django.utils import timezone
from django.core.management.base import BaseCommand
from expenses.email_service import send_monthly_expense_report

class Command(BaseCommand):
    help = "Email the previous month's expense report to all active email-list recipients."

    def handle(self, *args, **options):
        today = timezone.localdate()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1

        count = send_monthly_expense_report(year, month)
        self.stdout.write(
            self.style.SUCCESS(
                f"Monthly report for {year}-{month:02d} sent to {count} recipient(s)."
            )
        )
