import logging
import smtplib
import socket

from django.conf import settings

from config.celery import app as celery_app

logger = logging.getLogger("apps.core.tasks")

_ERROR_CATEGORY_UNKNOWN = "unknown"
_ERROR_CATEGORY_TRANSIENT = "transient"
_ERROR_CATEGORY_PERMANENT = "permanent"

# Transient failures: provider/network-side conditions that may clear up on a
# retry. Retried with bounded exponential backoff.
_TRANSIENT_ERRORS = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPResponseException,
    socket.timeout,
    TimeoutError,
    ConnectionError,
    OSError,
)

# Permanent failures: configuration or recipient problems that retrying cannot
# fix. Never retried — surfaced clearly and promptly.
_PERMANENT_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPDataError,
)


def _retry_countdown(retries):
    """Exponential backoff (60s, 120s, 240s), bounded by max_retries."""
    return 60 * (2 ** retries)


@celery_app.task(name="core.ping")
def ping(message=None):
    """Infrastructure proof: exercises broker -> worker -> result backend."""
    return {"task_id": ping.request.id, "message": message}


@celery_app.task(
    name="core.send_invitation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_invitation_email(self, invitation_id):
    """Deliver a team-invitation email asynchronously (AUD-015).

    Idempotency: the task receives only the invitation primary key and
    re-reads current state at execution time. If the invitation has been
    accepted, expired, or cancelled since enqueue, the task does nothing —
    a worker retry can never resurrect an email for revoked state, and a
    cancelled invite is never re-emailed.

    Failures: transient SMTP/network errors retry with bounded exponential
    backoff (``_retry_countdown``, ``max_retries=3``); permanent errors
    (bad credentials, rejected recipients, malformed config) return a
    ``permanent_failure`` result without retrying. Unexpected exceptions
    propagate and mark the task FAILURE in the result backend.

    Never logs tokens, credentials, or full recipient addresses.
    """
    from apps.core.mail import build_invitation_message, redact_email

    kind = "invitation"

    try:
        from apps.accounts.models import Invitation

        invitation = Invitation.objects.select_related("tenant").get(pk=invitation_id)
    except Invitation.DoesNotExist:
        logger.warning(
            "email task skipped: invitation does not exist",
            extra={"kind": kind, "invitation_id": str(invitation_id)},
        )
        return {
            "kind": kind,
            "invitation_id": str(invitation_id),
            "status": "skipped",
            "reason": "missing",
        }

    if invitation.is_accepted():
        _log_skip(kind, invitation, "already_accepted")
        return _skipped_result(invitation_id, "already_accepted")
    if invitation.is_expired():
        _log_skip(kind, invitation, "expired")
        return _skipped_result(invitation_id, "expired")

    recipient = redact_email(invitation.email)
    try:
        message = build_invitation_message(invitation)
        message.send()
    except _PERMANENT_ERRORS as exc:
        logger.error(
            "email task permanent failure",
            extra={
                "kind": kind,
                "invitation_id": str(invitation_id),
                "recipient": recipient,
                "error_category": _ERROR_CATEGORY_PERMANENT,
                "error_type": type(exc).__name__,
                "attempt": self.request.retries + 1,
            },
        )
        return {
            "kind": kind,
            "invitation_id": str(invitation_id),
            "status": "permanent_failure",
            "error_category": _ERROR_CATEGORY_PERMANENT,
            "error_type": type(exc).__name__,
            "attempt": self.request.retries + 1,
        }
    except _TRANSIENT_ERRORS as exc:
        logger.info(
            "email task transient failure, scheduling retry",
            extra={
                "kind": kind,
                "invitation_id": str(invitation_id),
                "recipient": recipient,
                "error_category": _ERROR_CATEGORY_TRANSIENT,
                "error_type": type(exc).__name__,
                "retry": self.request.retries + 1,
            },
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))

    logger.info(
        "email task sent",
        extra={
            "kind": kind,
            "invitation_id": str(invitation_id),
            "recipient": recipient,
            "status": "sent",
            "attempt": self.request.retries + 1,
            "backend": settings.EMAIL_BACKEND,
        },
    )
    return {
        "kind": kind,
        "invitation_id": str(invitation_id),
        "status": "sent",
        "recipient": recipient,
        "attempt": self.request.retries + 1,
        "task_id": self.request.id,
    }


def _log_skip(kind, invitation, reason):
    from apps.core.mail import redact_email

    logger.info(
        "email task skipped: invitation no longer actionable",
        extra={
            "kind": kind,
            "invitation_id": str(invitation.id),
            "recipient": redact_email(invitation.email),
            "reason": reason,
        },
    )


def _skipped_result(invitation_id, reason):
    return {
        "kind": "invitation",
        "invitation_id": str(invitation_id),
        "status": "skipped",
        "reason": reason,
    }