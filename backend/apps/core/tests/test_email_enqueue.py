"""B1: a broker that cannot be reached must not fail a committed invitation.

``transaction.on_commit`` runs *after* the invitation row is committed, so a
publication failure used to escape the view as an unexplained HTTP 500 while the
invitation sat there, valid and undispatched. The unreachable-broker tests below
drive the real publish path (eager mode off, a host that can never resolve)
rather than mocking ``delay()``, so the exception taxonomy under test is the one
production sees. The live-broker tests do the same against a real Redis.
See ``apps.core.mail.enqueue_invitation_email``.
"""

import datetime as dt_mod
import os
import time

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Invitation, Membership, User
from apps.accounts.services import InvitationService
from apps.accounts.tests.helpers import login
from apps.core.mail import enqueue_invitation_email
from apps.core.models import Tenant
from apps.core.tasks import send_invitation_email
from config.celery import app as celery_app

from .conftest import UNREACHABLE_BROKER, publish_via

# A broker URL carrying a credential, to prove the failure log leaks neither it
# nor anything else it could carry.
BROKER_WITH_SECRET = "redis://cetrak-user:hunter2-super-secret@cetrak-broker.invalid:6379/0"

requires_live_broker = pytest.mark.skipif(
    os.environ.get("CETRAK_CELERY_INTEGRATION") != "1",
    reason="Real broker publish path only runs with CETRAK_CELERY_INTEGRATION=1 "
    "(a Redis on CELERY_BROKER_URL, e.g. `docker compose --profile worker up`).",
)


class InvitationPublishTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        response = login(self.client, "admin@example.com", "SecurePass123")
        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {response.data['access']}",
            "HTTP_X_TENANT_ID": str(self.tenant.id),
        }

    def create_invitation(self, email):
        """POST an invitation and let the on_commit callback actually run."""
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("tenant-invitations"),
                {"email": email, "role": "Accountant"},
                format="json",
                **self.headers,
            )

    def make_invitation(self, email, token):
        return Invitation.objects.create(
            email=email,
            role="Accountant",
            token=token,
            tenant_id=self.tenant.id,
            expires_at=timezone.now() + dt_mod.timedelta(days=7),
        )


class UnreachableBrokerTests(InvitationPublishTestCase):
    """No broker required: `.invalid` can never resolve, on any machine."""

    def test_unreachable_broker_still_returns_201_with_one_invitation(self):
        with publish_via(UNREACHABLE_BROKER):
            response = self.create_invitation("newuser@example.com")

            assert response.status_code == status.HTTP_201_CREATED
            invitations = Invitation.objects.filter(
                email="newuser@example.com", tenant_id=self.tenant.id
            )
            assert invitations.count() == 1, "a failed dispatch must not duplicate it"
            assert response.data["id"] == str(invitations.get().id)
            assert len(mail.outbox) == 0

    def test_committed_invitation_stays_usable_after_broker_failure(self):
        with publish_via(UNREACHABLE_BROKER):
            self.create_invitation("newuser@example.com")
        invitation = Invitation.objects.get(email="newuser@example.com")

        accepted, error = InvitationService().validate_token(invitation.token)

        assert error is None
        assert accepted.email == "newuser@example.com"

    def test_broker_failure_is_logged_with_operational_context(self):
        with self.assertLogs("apps.core.mail", level="ERROR") as captured:
            with publish_via(UNREACHABLE_BROKER):
                self.create_invitation("newuser@example.com")

        assert len(captured.records) == 1
        record = captured.records[0]
        invitation = Invitation.objects.get(email="newuser@example.com")
        assert record.invitation_id == str(invitation.id)
        assert record.error_type
        assert record.broker == "unreachable"
        assert "not dispatched" in record.getMessage()

    def test_broker_failure_log_carries_no_secret_token_or_broker_url(self):
        with self.assertLogs("apps.core.mail", level="DEBUG") as captured:
            with publish_via(BROKER_WITH_SECRET):
                self.create_invitation("newuser@example.com")
        invitation = Invitation.objects.get(email="newuser@example.com")

        logged = "\n".join(
            f"{record.getMessage()} {record.__dict__}" for record in captured.records
        )
        for secret in (
            "hunter2-super-secret",
            "cetrak-user",
            invitation.token,
            "SecurePass123",
            "cetrak-broker.invalid",
        ):
            assert secret not in logged, f"{secret!r} leaked into the failure log"

    def test_enqueue_reports_the_failure_instead_of_raising(self):
        invitation = self.make_invitation("direct@example.com", "direct-token")

        with publish_via(UNREACHABLE_BROKER):
            result = enqueue_invitation_email(invitation.id)

            assert result is None
        assert Invitation.objects.filter(pk=invitation.pk).exists()

    def test_broker_failure_does_not_alter_task_retry_configuration(self):
        before = (send_invitation_email.max_retries, send_invitation_email.default_retry_delay)
        assert before == (3, 60)

        with publish_via(UNREACHABLE_BROKER):
            self.create_invitation("newuser@example.com")

        after = (send_invitation_email.max_retries, send_invitation_email.default_retry_delay)
        assert after == before


@requires_live_broker
class LiveBrokerPublishTests(InvitationPublishTestCase):
    """The same seam against a real Redis broker: the message must really land."""

    def test_message_reaches_the_configured_broker(self):
        from kombu import Connection, Queue

        with publish_via(celery_app.conf.broker_url) as app:
            if app.control.inspect(timeout=2).ping():
                pytest.skip(
                    "a live worker is consuming the queue, so the published message "
                    "is taken before it can be read back; "
                    "test_celery_integration.py covers the consumed case"
                )

            messages = []
            with Connection(app.conf.broker_url) as connection:
                # The Redis transport stores a direct-exchange message under the
                # routing key, so the queue is readable without a worker declaring
                # it. Purged *before* the publish: the broker is a developer's own
                # Redis and may still hold messages from an earlier run.
                queue = Queue("celery", channel=connection.default_channel)
                queue.purge()

                response = self.create_invitation("queued@example.com")
                assert response.status_code == status.HTTP_201_CREATED
                invitation = Invitation.objects.get(email="queued@example.com")

                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    message = queue.get(no_ack=True)
                    if message is None:
                        time.sleep(0.05)
                        continue
                    messages.append(message)
                    if message.headers.get("task") == "core.send_invitation_email":
                        break

        published = [m for m in messages if m.headers.get("task") == "core.send_invitation_email"]
        assert len(published) == 1, f"expected one publish, got {len(messages)} message(s)"
        assert published[0].headers["id"]
        assert str(invitation.id) in str(published[0].payload)
        assert len(mail.outbox) == 0, "the web process must not send the mail itself"

    def test_enqueue_returns_an_async_result_against_a_live_broker(self):
        invitation = self.make_invitation("live@example.com", "live-token")

        with publish_via(celery_app.conf.broker_url) as app:
            result = enqueue_invitation_email(invitation.id)

            assert result is not None
            assert result.id
            assert app.conf.task_always_eager is False
