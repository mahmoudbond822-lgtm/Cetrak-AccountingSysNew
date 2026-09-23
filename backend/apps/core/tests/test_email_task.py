import datetime as dt_mod
import logging
import smtplib
import socket
from unittest import mock

import pytest
from celery.exceptions import Retry
from django.core import mail
from django.utils import timezone

from apps.accounts.models import Invitation, User
from apps.core.models import Tenant
from apps.core.tasks import _retry_countdown, send_invitation_email


def _make_invitation(**overrides):
    tenant = Tenant.objects.create(name="Acme Inc")
    defaults = dict(
        email="invited@example.com",
        role="Accountant",
        token="inv-token-abc123",
        tenant_id=tenant.id,
        expires_at=timezone.now() + dt_mod.timedelta(days=7),
    )
    defaults.update(overrides)
    return Invitation.objects.create(**defaults)


@pytest.mark.django_db
class TestTaskRegistration:
    def test_registered_with_bounded_max_retries(self):
        assert send_invitation_email.name == "core.send_invitation_email"
        assert send_invitation_email.max_retries == 3
        assert send_invitation_email.default_retry_delay == 60

    @pytest.mark.parametrize("retries,expected", [
        (0, 60),
        (1, 120),
        (2, 240),
    ])
    def test_retry_countdown_is_bounded_exponential(self, retries, expected):
        assert _retry_countdown(retries) == expected

    def test_task_is_discoverable_by_celery(self):
        from config.celery import app as celery_app
        assert "core.send_invitation_email" in celery_app.tasks


@pytest.mark.django_db
class TestTaskExecution:
    def test_success_returns_sent_metadata_and_sends(self):
        invitation = _make_invitation()
        result = send_invitation_email.delay(str(invitation.id)).get()
        assert result["status"] == "sent"
        assert result["kind"] == "invitation"
        assert result["recipient"] == "i*****d@example.com"
        assert result["invitation_id"] == str(invitation.id)
        assert "i***d@example.com" != invitation.email
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["invited@example.com"]
        assert "inv-token-abc123" in mail.outbox[0].body

    def test_missing_invitation_skipped_silently(self):
        result = send_invitation_email.delay("00000000-0000-0000-0000-000000000000").get()
        assert result["status"] == "skipped"
        assert result["reason"] == "missing"
        assert len(mail.outbox) == 0

    def test_accepted_invitation_skipped(self):
        invitation = _make_invitation(accepted_at=timezone.now())
        result = send_invitation_email.delay(str(invitation.id)).get()
        assert result["status"] == "skipped"
        assert result["reason"] == "already_accepted"
        assert len(mail.outbox) == 0

    def test_expired_invitation_skipped(self):
        invitation = _make_invitation(
            expires_at=timezone.now() - dt_mod.timedelta(days=1)
        )
        result = send_invitation_email.delay(str(invitation.id)).get()
        assert result["status"] == "skipped"
        assert result["reason"] == "expired"
        assert len(mail.outbox) == 0

    def test_cancelled_invitation_never_emailed(self):
        invitation = _make_invitation()
        invitation_id = str(invitation.id)
        invitation.delete()
        result = send_invitation_email.delay(invitation_id).get()
        assert result["status"] == "skipped"
        assert result["reason"] == "missing"
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestTaskFailureClassification:
    def _invitee_with_failing_send(self, exc):
        invitation = _make_invitation()
        msg = mock.MagicMock()
        msg.send.side_effect = exc
        patch = mock.patch("apps.core.mail.build_invitation_message", return_value=msg)
        return invitation, patch

    def test_transient_failure_schedules_retry_with_backoff(self):
        invitation, patch = self._invitee_with_failing_send(socket.timeout("t"))
        with patch:
            with pytest.raises(Retry) as exc_info:
                send_invitation_email.delay(str(invitation.id)).get()
        assert exc_info.value.when == 60

    def test_connection_error_treated_transient(self):
        invitation, patch = self._invitee_with_failing_send(ConnectionError("down"))
        with patch:
            with pytest.raises(Retry):
                send_invitation_email.delay(str(invitation.id)).get()

    def test_permanent_failure_returns_without_retry(self):
        invitation, patch = self._invitee_with_failing_send(
            smtplib.SMTPAuthenticationError(535, b"bad credentials")
        )
        with patch:
            result = send_invitation_email.delay(str(invitation.id)).get()
        assert result["status"] == "permanent_failure"
        assert result["error_category"] == "permanent"
        assert result["error_type"] == "SMTPAuthenticationError"
        assert result["attempt"] == 1
        assert len(mail.outbox) == 0

    def test_recipient_refused_treated_permanent(self):
        invitation, patch = self._invitee_with_failing_send(
            smtplib.SMTPRecipientsRefused(recipients={"bad@example.com": (550, b"nope")})
        )
        with patch:
            result = send_invitation_email.delay(str(invitation.id)).get()
        assert result["status"] == "permanent_failure"

    def test_unexpected_error_propagates(self):
        invitation, patch = self._invitee_with_failing_send(RuntimeError("boom"))
        with patch:
            with pytest.raises(RuntimeError):
                send_invitation_email.delay(str(invitation.id)).get()


@pytest.mark.django_db
class TestTaskLoggingSecurity:
    @pytest.fixture(autouse=True)
    def _secret(self, monkeypatch):
        monkeypatch.setattr("django.conf.settings.EMAIL_HOST_PASSWORD", "super-secret-pw")

    def test_logs_use_redacted_recipient_never_full_email(self, caplog):
        invitation = _make_invitation()
        with caplog.at_level(logging.INFO, logger="apps.core.tasks"):
            send_invitation_email.delay(str(invitation.id)).get()
        tasks_log = "\n".join(
            r.getMessage() + " " + repr(getattr(r, "recipient", ""))
            for r in caplog.records
            if r.name == "apps.core.tasks"
        )
        assert "i*****d@example.com" in tasks_log
        assert invitation.email not in tasks_log

    def test_logs_never_contain_token_or_credentials(self, caplog):
        invitation = _make_invitation()
        with caplog.at_level(logging.INFO, logger="apps.core.tasks"):
            send_invitation_email.delay(str(invitation.id)).get()
        assert "inv-token-abc123" not in caplog.text
        assert "super-secret-pw" not in caplog.text
        assert "smtp.example.com" not in caplog.text


@pytest.mark.django_db
class TestEnqueue:
    def test_enqueue_returns_async_result(self):
        from apps.core.mail import enqueue_invitation_email
        result = enqueue_invitation_email(str(_make_invitation().id))
        assert result.id
        assert result.state in ("SUCCESS", "FAILURE")