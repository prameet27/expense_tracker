# Automatic birthday/anniversary and monthly report emails

The project now supports:

1. Birthday/anniversary reminders:
   - Add a reminder from **Reminders**.
   - Set `Remind days before` to 0 for the event day, or e.g. 7 for one week before.
   - The email is sent automatically to the reminder creator's profile email.
   - Each occurrence is sent only once.

2. Monthly expense report email list:
   - Open **Monthly Report Emails**.
   - Add every address that should receive the report.
   - On the first day of each month, the previous month's PDF report is sent to every active address.

## Gmail configuration

Use a Gmail App Password, not your normal Gmail password.

Set these environment variables before starting Django:

```bash
export EMAIL_HOST_USER="youraccount@gmail.com"
export EMAIL_HOST_PASSWORD="your-16-character-app-password"
```

## Database migration

```bash
python manage.py migrate
```

## Test manually

Send due reminders:

```bash
python manage.py send_reminders
```

Send the previous month's report:

```bash
python manage.py send_monthly_report
```

## Automatic scheduling on Ubuntu/Linux

Edit the user's crontab:

```bash
crontab -e
```

Run reminders every day at 09:00:

```cron
0 9 * * * cd /path/to/expense_tracker && /path/to/venv/bin/python manage.py send_reminders >> /path/to/expense_tracker/email_cron.log 2>&1
```

Run the monthly report on the first day of every month at 09:15:

```cron
15 9 1 * * cd /path/to/expense_tracker && /path/to/venv/bin/python manage.py send_monthly_report >> /path/to/expense_tracker/email_cron.log 2>&1
```

Replace `/path/to/expense_tracker` and `/path/to/venv/bin/python` with your actual paths.
