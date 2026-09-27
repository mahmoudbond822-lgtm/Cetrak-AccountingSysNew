"""Email delivery helpers (AUD-015).

The only email currently required by Cetrak is the team-invitation dispatch
(spec 002-team-invitations, US1). This module owns message construction from
committed application state, recipient redaction for safe logging, and the
async enqueue seam. The actual transport runs in a Celery task
(``apps.core.tasks.send_invitation_email``) so HTTP requests are never blocked
by SMTP.

Security contract (invariant):
  * No token, password, SMTP credential, or provider API secret is ever logged.
  * Message bodies are rendered from server-controlled templates only; dynamic
    values are auto-escaped by Django's template engine.
  * The task re-reads invitation state at execution time and refuses to email
    invitations that have been accepted, expired, or cancelled after enqueue.

Delivery semantics: the invitation row is committed before the enqueue runs, so
a broker that cannot be reached is reported, not raised. The caller gets a
``None`` handle and an ERROR log line, and the invitation stays exactly as it
was. Re-sending is an operator decision (there is no resend endpoint).
"""

import logging

from celery.exceptions import CeleryError
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from kombu.exceptions import KombuError
from redis.exceptions import RedisError

logger = logging.getLogger("apps.core.mail")

# Publishing to the broker can fail for reasons no caller can act on. Observed
# on the real publish path: kombu.exceptions.OperationalError when the broker
# refuses the connection, a plain RuntimeError ("retry limit exceeded ... result
# store backend") when the result backend is unreachable, and redis exceptions
# when the client itself fails. kombu and redis ship with celery/redis in
# requirements/base.txt, so importing them here adds no dependency.
BROKER_TRANSPORT_ERRORS = (CeleryError, KombuError, RedisError, OSError, RuntimeError)


def redact_email(email):
    """Mask an email address for safe log output (PII-conscious)."""
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    if len(local) <= 2:
        visible = local[0]
    else:
        visible = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{visible}@{domain}"


def invitation_action_url(invitation_token):
    """Build the invitee-facing registration link from configured app URLs."""
    base = (settings.FRONTEND_URL or "").rstrip("/")
    return f"{base}/register?token={invitation_token}"


def build_invitation_message(invitation):
    """Render both alternatives and return a ready-to-send email message.

    ``invitation`` must be an ``Invitation`` with ``tenant`` selected/loaded.
    The token is embedded in the action link (that is the delivery mechanism)
    but never placed in logs or audit data.
    """
    context = {
        "tenant_name": invitation.tenant.name,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
        "action_url": invitation_action_url(invitation.token),
        "invited_email": invitation.email,
    }
    text_body = render_to_string("email/invitation_email.txt", context)
    html_body = render_to_string("email/invitation_email.html", context)
    message = EmailMultiAlternatives(
        subject=f"You're invited to join {invitation.tenant.name} on Cetrak",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.email],
    )
    message.attach_alternative(html_body, "text/html")
    return message


def enqueue_invitation_email(invitation_id):
    """Dispatch invitation email delivery to the Celery worker (async).

    Must be called after the invitation row is committed (the view wires this
    through ``transaction.on_commit``). Returns the ``AsyncResult`` handle, or
    ``None`` when the message could not be published.

    A publication failure is logged and swallowed rather than raised: the caller
    runs after the commit, so raising would turn a delivered invitation into an
    unexplained HTTP 500 while the row sits there undispatched. Only the
    exception *type* is logged — kombu/redis messages can embed the broker URL
    and its credentials.
    """
    from apps.core.tasks import send_invitation_email

    try:
        result = send_invitation_email.delay(str(invitation_id))
    except BROKER_TRANSPORT_ERRORS as exc:
        logger.error(
            "email task enqueue failed: invitation is committed but not "
            "dispatched, so the invitee will not be emailed until it is re-sent",
            extra={
                "kind": "invitation",
                "invitation_id": str(invitation_id),
                "error_type": type(exc).__name__,
                "broker": "unreachable",
            },
        )
        return None
    logger.info(
        "email task enqueued",
        extra={
            "kind": "invitation",
            "task_id": result.id,
            "invitation_id": str(invitation_id),
        },
    )
    return result
