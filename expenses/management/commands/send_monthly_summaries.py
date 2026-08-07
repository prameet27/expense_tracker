from django.core.management.base import BaseCommand
from expenses.notifications import check_and_send_monthly_summaries

class Command(BaseCommand):
    help = "Send end-of-month expense summary notifications to all Users (idempotent - safe to run repeatedly)"

    def handle(self, *args, **options):
        check_and_send_monthly_summaries()
        self.stdout.write(self.style.SUCCESS("Monthly summary check complete."))