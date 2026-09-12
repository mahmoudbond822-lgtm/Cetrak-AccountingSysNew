import datetime as dt_mod

from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Tenant, AuditLog
from apps.accounts.models import User, Membership, Invitation


class InvitationBindingTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        self.register_url = reverse("auth-register")

    def _create_invitation(self, email="boss@example.com", **overrides):
        defaults = dict(
            email=email,
            role="Accountant",
            token="binding-token",
            tenant_id=self.tenant.id,
            expires_at=timezone.now() + dt_mod.timedelta(days=7),
        )
        defaults.update(overrides)
        return Invitation.objects.create(**defaults)

    def _register(self, email, password="SecurePass123", token="binding-token"):
        return self.client.post(
            self.register_url,
            {
                "email": email,
                "password": password,
                "company_name": "Ignored",
                "invitation_token": token,
            },
            format="json",
        )

    def test_matching_email_accepts_and_grants_membership(self):
        self._create_invitation()
        response = self._register("boss@example.com")
        assert response.status_code == status.HTTP_201_CREATED
        assert "refresh" not in response.data
        user = User.objects.get(email="boss@example.com")
        assert Membership.objects.filter(user=user, tenant=self.tenant).exists()
        invitation = Invitation.objects.get(token="binding-token")
        assert invitation.accepted_at is not None

    def test_different_email_rejected_and_no_user_left_behind(self):
        self._create_invitation()
        response = self._register("intruder@example.com")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.filter(email__iexact="intruder@example.com").exists() is False
        assert Membership.objects.filter(
            user__email__iexact="intruder@example.com"
        ).count() == 0

    def test_mismatch_error_does_not_reveal_invited_email(self):
        self._create_invitation(email="secret-contact@example.com")
        response = self._register("intruder@example.com")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = str(response.data)
        assert "secret-contact@example.com" not in body
        assert "different email address" in body.lower()

    def test_case_variation_is_accepted(self):
        self._create_invitation(email="Invited@Example.COM")
        response = self._register("INVITED@example.com")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email__iexact="INVITED@example.com")
        assert Membership.objects.filter(user=user, tenant=self.tenant).exists()

    def test_existing_user_with_wrong_email_not_granted_membership(self):
        user = User.objects.create_user(email="existing@example.com", password="SecurePass123")
        other_tenant = Tenant.objects.create(name="Other")
        Membership.objects.create(user=user, tenant=other_tenant, role=Membership.Role.ADMIN)

        self._create_invitation(email="boss@example.com")
        response = self._register("existing@example.com")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Membership.objects.filter(user=user, tenant=self.tenant).exists() is False
        assert Membership.objects.filter(user=user).count() == 1

    def test_invitation_stored_canonical_lowercase(self):
        from apps.accounts.services import InvitationService
        service = InvitationService()
        invitation = service.create_invitation(
            email="  Boss@Example.COM ",
            role="Accountant",
            tenant_id=self.tenant.id,
        )
        assert invitation.email == "boss@example.com"

    def test_failed_attempt_leaves_invitation_reusable_by_correct_email(self):
        self._create_invitation()
        first = self._register("wrong@example.com")
        assert first.status_code == status.HTTP_400_BAD_REQUEST

        second = self._register("boss@example.com")
        assert second.status_code == status.HTTP_201_CREATED
        assert Membership.objects.filter(
            user__email="boss@example.com", tenant=self.tenant
        ).exists()

    def test_invite_accept_audited(self):
        self._create_invitation()
        self._register("boss@example.com")
        user = User.objects.get(email="boss@example.com")
        audit = AuditLog.objects.filter(action="invitation.accept").first()
        assert audit is not None
        assert str(audit.actor_id) == str(user.id)
        assert str(audit.tenant_id) == str(self.tenant.id)