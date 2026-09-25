import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

def send_reminder_email(recipients, subject, message):
    """
    Send a reminder email. `recipients` may be a single User instance
    (kept for backwards compatibility) or a list/iterable of email
    address strings.
    """
    if hasattr(recipients, "email"):
        # A User instance was passed in - fall back to old single-user behavior.
        recipient_list = [recipients.email] if recipients.email else []
        log_target = getattr(recipients, "username", recipients.email)
    else:
        recipient_list = [r for r in recipients if r]
        log_target = ", ".join(recipient_list)

    if not recipient_list:
        logger.info("Skipping reminder email for %s: no email address on file", log_target)
        return False

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.warning("Skipping reminder email: Email Host User / Email Host Password not configured")

    try:
        send_mail(
            subject=subject, message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list, fail_silently=False,
        )
        return True

    except Exception:
        logger.exception("Failed to send reminder email to %s", log_target)
        return False