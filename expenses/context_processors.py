from .models import Notification
from .notifications import check_and_send_monthly_summaries

def notifications(request):
    if request.user.is_authenticated:
        check_and_send_monthly_summaries()
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    else:
        count = 0
    return {'unread_notifications_count': count}