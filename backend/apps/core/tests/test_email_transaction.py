from django.conf import settings
from django.core import mail
from django.db import transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Invitation, Membership, User
from apps.core.models import Tenant


class InvitationEmailDispatchTests(APITestCase):
    """End-to-end wiring: invitation creation -> on_commit -> email task."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "admin@example.com", "password": "SecurePass123"},
            format="json",
        )
        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {login.data['access']}",
            "HTTP_X_TENANT_ID": str(self.tenant.id),
        }

    def url(self):
        return reverse("tenant-invitations")

    def test_email_is_delivered_only_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                self.url(),
                {"email": "newuser@example.com", "role": "Accountant"},
                format="json",
                **self.headers,
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert len(mail.outbox) == 0
        assert len(callbacks) >= 1
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["newuser@example.com"]
        invitation = Invitation.objects.get(
            email="newuser@example.com", tenant_id=self.tenant.id
        )
        action_url = f"{settings.FRONTEND_URL}/register?token={invitation.token}"
        assert action_url in sent.body
        assert action_url in sent.alternatives[0][0]
        assert "Test Corp" in sent.subject

    def test_rollback_produces_no_email(self):
        with transaction.atomic():
            response = self.client.post(
                self.url(),
                {"email": "rollback@example.com", "role": "Accountant"},
                format="json",
                **self.headers,
            )
            assert response.status_code == status.HTTP_201_CREATED
            transaction.set_rollback(True)
        assert len(mail.outbox) == 0
        assert not Invitation.objects.filter(email="rollback@example.com").exists()

    def test_no_dispatch_when_creation_rejected(self):
        response = self.client.post(
            self.url(),
            {"email": "not-an-email", "role": "Accountant"},
            format="json",
            **self.headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert len(mail.outbox) == 0

    def test_email_backend_is_locmem_in_tests(self):
        assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"