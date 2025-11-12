import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import User

logger = logging.getLogger(__name__)


@shared_task()
def get_users_count():
    """A pointless Celery task to demonstrate usage."""
    return User.objects.count()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_email, reset_url, uid, token):
    """
    Send password reset email asynchronously via Mailgun.

    Args:
        user_email: User's email address
        reset_url: Frontend URL for password reset
        uid: Base64-encoded user ID
        token: Password reset token

    Retries: 3 times with 60-second delay between attempts
    """
    try:
        # Construct the full reset link
        reset_link = f"{reset_url}?uid={uid}&token={token}"

        # Email context
        context = {
            "reset_link": reset_link,
            "user_email": user_email,
            "site_name": "Quran Backend",
        }

        # Render HTML email template
        html_message = render_to_string("users/emails/password_reset.html", context)
        plain_message = strip_tags(html_message)

        # Send email via Mailgun (configured in settings)
        send_mail(
            subject="Password Reset Request - Quran Backend",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )

    except Exception as exc:
        # Log exception with stack trace and retry
        logger.exception(
            "Failed to send password reset email to %s",
            user_email,
            extra={"email": user_email, "task_id": self.request.id, "error": str(exc)},
        )
        # Retry the task and preserve the original exception context
        raise self.retry(exc=exc) from exc

    else:
        logger.info(
            "Password reset email sent successfully to %s",
            user_email,
            extra={"email": user_email, "task_id": self.request.id},
        )

        return {"status": "success", "email": user_email}
