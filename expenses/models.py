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
        return self.title


class EmailRecipient(models.Model):
    """
    Email addresses that receive automatic birthday,
    anniversary and other reminder emails.
    """
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    added_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_recipients"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return f"{self.name} <{self.email}>" if self.name else self.email

class Notification(models.Model):
    VERB_CHOICES = [
        ('created', 'created'),
        ('updated', 'updated'),
        ('deleted', 'deleted'),
        ('summary', 'monthly summary'),
        ('reminder', 'reminder'),
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
    """
    Tracks which (year, month) combinations have already had their
    household-wide summary notification sent, so it's only ever sent once.
    """
    year = models.IntegerField()
    month = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('year', 'month')

    def __str__(self):
        return f"Household summary for {self.month}/{self.year}"


class Reminder(models.Model):
    REMINDER_TYPES = [
        ('birthday', 'Birthday'),
        ('anniversary', 'Anniversary'),
        ('other', 'Other'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    person_name = models.CharField(max_length=100)
    email = models.EmailField(
        blank=True,
        help_text="The person's own email address, so the wish email can be sent directly to them.",
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    # The original birth date / wedding date / event date. Only month+day
    # repeat every year; the year is kept so we can show "turns 30", "5th
    # anniversary", etc.
    original_date = models.DateField()
    reminder1_days_before = models.PositiveIntegerField(
        default=0, help_text="First reminder. 0 = remind on the day itself"
    )
    reminder2_days_before = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Optional second reminder, e.g. a week earlier. Leave blank to send only one reminder.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['person_name']

    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.person_name}"

    def next_occurrence(self, today=None):
        """The next upcoming date (this year or next) this reminder falls on."""
        from datetime import date as date_cls
        today = today or date_cls.today()
        try:
            this_year = self.original_date.replace(year=today.year)
        except ValueError:
            # Feb 29 on a non-leap year
            this_year = self.original_date.replace(year=today.year, day=28)
        if this_year < today:
            try:
                this_year = self.original_date.replace(year=today.year + 1)
            except ValueError:
                this_year = self.original_date.replace(year=today.year + 1, day=28)
        return this_year

    def reminder_dates(self, today=None):
        """
        Returns a list of (slot, days_before, send_date) tuples for the
        upcoming occurrence - one for reminder1, and one for reminder2 if set.
        """
        from datetime import timedelta

        occurrence = self.next_occurrence(today)
        dates = [("r1", self.reminder1_days_before, occurrence - timedelta(days=self.reminder1_days_before))]
        if self.reminder2_days_before is not None:
            dates.append(("r2", self.reminder2_days_before, occurrence - timedelta(days=self.reminder2_days_before)))
        return dates

    def due_slots_today(self, today=None):
        """Which reminder slot(s), if any, fall due today and haven't been sent yet for this year."""
        from datetime import date as date_cls
        today = today or date_cls.today()
        occurrence_year = self.next_occurrence(today).year
        due = []
        for slot, days_before, send_date in self.reminder_dates(today):
            if send_date != today:
                continue
            if ReminderLog.objects.filter(reminder=self, year=occurrence_year, slot=slot).exists():
                continue
            due.append(slot)
        return due

    def default_wish_subject(self):
        kind = self.get_reminder_type_display()
        return f"{kind} Wishes for {self.person_name}!"

    def default_wish_message(self, today=None):
        from datetime import date as date_cls
        today = today or date_cls.today()
        occurrence = self.next_occurrence(today)
        years_count = today.year - self.original_date.year

        if self.reminder_type == "birthday":
            body = f"Happy Birthday, {self.person_name}! Wishing you a wonderful {years_count}th birthday on {occurrence.strftime('%B %d, %Y')}."
        elif self.reminder_type == "anniversary":
            body = f"Happy Anniversary, {self.person_name}! Wishing you a wonderful {years_count} year(s) together, celebrated on {occurrence.strftime('%B %d, %Y')}."
        else:
            body = f"Just a reminder about {self.person_name} - {self.get_reminder_type_display()} on {occurrence.strftime('%B %d, %Y')}."

        if self.notes:
            body += f"\n\n{self.notes}"
        return body


class ReminderLog(models.Model):
    """Tracks which (reminder, year, slot) combinations have already been notified."""
    SLOT_CHOICES = [
        ("r1", "Reminder 1"),
        ("r2", "Reminder 2"),
    ]

    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE)
    year = models.IntegerField()
    slot = models.CharField(max_length=2, choices=SLOT_CHOICES, default="r1")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reminder', 'year', 'slot')