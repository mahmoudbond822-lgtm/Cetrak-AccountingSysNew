import pytest
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.accounts.models import User, Membership


def _admin_headers(client):
    resp = client.post(
        reverse("auth-login"),
        {"email": "admin@example.com", "password": "SecurePass123"},
        format="json",
    )
    token = resp.data["access"]
    tenant_id = resp.data["active_tenant"]["id"]
    return {
        "HTTP_AUTHORIZATION": f"Bearer {token}",
        "HTTP_X_TENANT_ID": str(tenant_id),
    }


def _non_admin_headers(client):
    token = client.post(
        reverse("auth-login"),
        {"email": "member@example.com", "password": "SecurePass123"},
        format="json",
    ).data["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}", "HTTP_X_TENANT_ID": ""}


class InvitationCreateTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        from apps.core.models import Tenant
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )

    def url(self):
        return reverse("tenant-invitations")

    def test_create_invitation_success_returns_201(self):
        headers = _admin_headers(self.client)
        response = self.client.post(
            self.url(),
            {"email": "newuser@example.com", "role": "Accountant"},
            format="json",
            **headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@example.com"
        assert response.data["role"] == "Accountant"
        assert response.data["status"] == "pending"
        assert "id" in response.data
        assert "expires_at" in response.data

    def test_create_invitation_non_admin_returns_403(self):
        headers = _non_admin_headers(self.client)
        headers["HTTP_X_TENANT_ID"] = str(self.tenant.id)
        response = self.client.post(
            self.url(),
            {"email": "newuser@example.com", "role": "Accountant"},
            format="json",
            **headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_pending_invitation_returns_400(self):
        from apps.accounts.models import Invitation
        Invitation.objects.create(
            email="duplicate@example.com",
            role="Accountant",
            token="existing-token",
            tenant_id=self.tenant.id,
            expires_at="2026-12-31T23:59:59Z",
        )
        headers = _admin_headers(self.client)
        response = self.client.post(
            self.url(),
            {"email": "duplicate@example.com", "role": "Accountant"},
            format="json",
            **headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invitation_no_auth_returns_401(self):
        response = self.client.post(
            self.url(),
            {"email": "newuser@example.com", "role": "Accountant"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class RegisterWithInvitationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        from apps.core.models import Tenant
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )

    def _create_invitation(self, **overrides):
        from apps.accounts.models import Invitation
        import datetime as dt_mod
        from django.utils import timezone
        defaults = dict(
            email="invited@example.com",
            role="Accountant",
            token="valid-token-123",
            tenant_id=self.tenant.id,
            expires_at=timezone.now() + dt_mod.timedelta(days=7),
        )
        defaults.update(overrides)
        return Invitation.objects.create(**defaults)

    def test_register_with_valid_invitation_token_returns_201(self):
        self._create_invitation()
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "invited@example.com",
                "password": "SecurePass123",
                "company_name": "Ignored Corp",
                "invitation_token": "valid-token-123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "tenants" in response.data
        assert len(response.data["tenants"]) == 1
        assert response.data["tenants"][0]["role"] == "Accountant"

    def test_register_with_expired_token_returns_400(self):
        import datetime as dt_mod
        from django.utils import timezone
        self._create_invitation(
            expires_at=timezone.now() - dt_mod.timedelta(days=1)
        )
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "invited@example.com",
                "password": "SecurePass123",
                "company_name": "Whatever",
                "invitation_token": "valid-token-123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_invalid_token_returns_400(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "some@example.com",
                "password": "SecurePass123",
                "company_name": "Whatever",
                "invitation_token": "nonexistent-token",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_accepted_token_returns_400(self):
        import datetime as dt_mod
        from django.utils import timezone
        self._create_invitation(accepted_at=timezone.now())
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "invited@example.com",
                "password": "SecurePass123",
                "company_name": "Whatever",
                "invitation_token": "valid-token-123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class ExistingUserInvitedTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant

        self.user = User.objects.create_user(
            email="existing@example.com", password="SecurePass123"
        )
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        Membership.objects.create(
            user=self.user, tenant=self.tenant_a, role=Membership.Role.ADMIN
        )

        self.other_admin = User.objects.create_user(
            email="otheradmin@example.com", password="SecurePass123"
        )
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        Membership.objects.create(
            user=self.other_admin, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )

    def test_existing_user_invited_sees_new_tenant_on_login(self):
        from apps.accounts.services import InvitationService
        inv = InvitationService().create_invitation(
            email="existing@example.com",
            role="Manager",
            tenant_id=self.tenant_b.id,
        )
        InvitationService().accept_invitation(inv.token, self.user)

        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": "existing@example.com", "password": "SecurePass123"},
            format="json",
        )
        assert login_resp.status_code == status.HTTP_200_OK
        tenant_names = {t["name"] for t in login_resp.data["tenants"]}
        assert "Tenant A" in tenant_names
        assert "Tenant B" in tenant_names

    def test_login_response_includes_all_memberships(self):
        from apps.accounts.services import InvitationService
        inv = InvitationService().create_invitation(
            email="existing@example.com",
            role="Accountant",
            tenant_id=self.tenant_b.id,
        )
        InvitationService().accept_invitation(inv.token, self.user)

        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": "existing@example.com", "password": "SecurePass123"},
            format="json",
        )
        assert login_resp.status_code == status.HTTP_200_OK
        assert len(login_resp.data["tenants"]) == 2


class TenantSwitchTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant

        self.user = User.objects.create_user(
            email="multi@example.com", password="SecurePass123"
        )
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        Membership.objects.create(
            user=self.user, tenant=self.tenant_a, role=Membership.Role.ADMIN
        )
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        Membership.objects.create(
            user=self.user, tenant=self.tenant_b, role=Membership.Role.MANAGER
        )

        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": "multi@example.com", "password": "SecurePass123"},
            format="json",
        )
        self.token = login_resp.data["access"]

    def test_switch_tenant_returns_new_token(self):
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_b.id]),
            **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert response.data["tenant"]["id"] == str(self.tenant_b.id)
        assert response.data["tenant"]["role"] == "Manager"

    def test_switch_tenant_no_membership_returns_404(self):
        from apps.core.models import Tenant
        other = Tenant.objects.create(name="Other")
        response = self.client.post(
            reverse("tenant-switch", args=[other.id]),
            **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_switch_tenant_unauthenticated_returns_401(self):
        from apps.core.models import Tenant
        other = Tenant.objects.create(name="Other")
        response = self.client.post(
            reverse("tenant-switch", args=[other.id]),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class MemberListTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant

        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        self.headers = _admin_headers(self.client)

    def test_list_members_returns_200_with_member_list(self):
        response = self.client.get(
            reverse("tenant-members"), **self.headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 2

    def test_list_members_non_admin_returns_403(self):
        headers = _non_admin_headers(self.client)
        headers["HTTP_X_TENANT_ID"] = str(self.tenant.id)
        response = self.client.get(
            reverse("tenant-members"), **headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class MemberRoleChangeTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant

        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        self.headers = _admin_headers(self.client)

    def test_change_member_role_returns_200(self):
        response = self.client.patch(
            reverse("tenant-member-role", args=[self.member.id]),
            {"role": "Manager"},
            format="json",
            **self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "Manager"

    def test_change_last_admin_role_returns_400(self):
        response = self.client.patch(
            reverse("tenant-member-role", args=[self.admin.id]),
            {"role": "Accountant"},
            format="json",
            **self.headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "last admin" in response.data["detail"].lower()


class MemberRemoveTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant

        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        self.headers = _admin_headers(self.client)

    def test_remove_member_returns_204(self):
        response = self.client.delete(
            reverse("tenant-member-remove", args=[self.member.id]),
            **self.headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_remove_last_admin_returns_400(self):
        response = self.client.delete(
            reverse("tenant-member-remove", args=[self.admin.id]),
            **self.headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "last admin" in response.data["detail"].lower()


class CancelInvitationTests(APITestCase):
    def setUp(self):
        from apps.core.models import Tenant
        from apps.accounts.models import Invitation

        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.tenant = Tenant.objects.create(name="Test Corp")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        self.invitation = Invitation.objects.create(
            email="pending@example.com",
            role="Accountant",
            token="cancel-token",
            tenant_id=self.tenant.id,
            expires_at="2026-12-31T23:59:59Z",
        )
        self.headers = _admin_headers(self.client)

    def test_list_pending_invitations_returns_200(self):
        response = self.client.get(
            reverse("tenant-invitations"), **self.headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_cancel_invitation_returns_204(self):
        response = self.client.delete(
            reverse("tenant-invitation-detail", args=[self.invitation.id]),
            **self.headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_register_with_cancelled_token_returns_400(self):
        self.client.delete(
            reverse("tenant-invitation-detail", args=[self.invitation.id]),
            **self.headers,
        )
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "pending@example.com",
                "password": "SecurePass123",
                "company_name": "Whatever",
                "invitation_token": "cancel-token",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class EdgeCaseTests(APITestCase):
    def setUp(self):
        self.admin_1 = User.objects.create_user(
            email="admin1@example.com", password="SecurePass123"
        )
        self.admin_2 = User.objects.create_user(
            email="admin2@example.com", password="SecurePass123"
        )
        from apps.core.models import Tenant
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        Membership.objects.create(
            user=self.admin_1, tenant=self.tenant_a, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.admin_2, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )

    def test_cross_tenant_duplicate_email_succeeds(self):
        """Same email can be invited to different tenants."""
        # Login admin1
        login_a = self.client.post(
            reverse("auth-login"),
            {"email": "admin1@example.com", "password": "SecurePass123"},
            format="json",
        )
        headers_a = {
            "HTTP_AUTHORIZATION": f"Bearer {login_a.data['access']}",
            "HTTP_X_TENANT_ID": str(login_a.data["active_tenant"]["id"]),
        }

        # Login admin2
        login_b = self.client.post(
            reverse("auth-login"),
            {"email": "admin2@example.com", "password": "SecurePass123"},
            format="json",
        )
        headers_b = {
            "HTTP_AUTHORIZATION": f"Bearer {login_b.data['access']}",
            "HTTP_X_TENANT_ID": str(login_b.data["active_tenant"]["id"]),
        }

        resp_a = self.client.post(
            reverse("tenant-invitations"),
            {"email": "same@example.com", "role": "Accountant"},
            format="json",
            **headers_a,
        )
        assert resp_a.status_code == status.HTTP_201_CREATED, f"resp_a data: {resp_a.data}"

        resp_b = self.client.post(
            reverse("tenant-invitations"),
            {"email": "same@example.com", "role": "Manager"},
            format="json",
            **headers_b,
        )
        assert resp_b.status_code == status.HTTP_201_CREATED

    def test_invite_existing_member_succeeds(self):
        """Existing member can also be invited (for role change via invite flow)."""
        token = self.client.post(
            reverse("auth-login"),
            {"email": "admin1@example.com", "password": "SecurePass123"},
            format="json",
        ).data["access"]
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_TENANT_ID": str(self.tenant_a.id),
        }

        resp = self.client.post(
            reverse("tenant-invitations"),
            {"email": "admin1@example.com", "role": "Accountant"},
            format="json",
            **headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_tenant_isolation_invitation_list(self):
        """Admin of tenant A cannot see tenant B's invitations."""
        Membership.objects.create(
            user=self.admin_1, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )
        token = self.client.post(
            reverse("auth-login"),
            {"email": "admin1@example.com", "password": "SecurePass123"},
            format="json",
        ).data["access"]

        from apps.accounts.models import Invitation
        from django.utils import timezone
        import datetime as dt
        Invitation.objects.create(
            email="secret@example.com",
            role="Manager",
            token="tenant-b-only-token",
            tenant_id=self.tenant_b.id,
            expires_at=timezone.now() + dt.timedelta(days=7),
        )

        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_TENANT_ID": str(self.tenant_a.id),
        }
        resp = self.client.get(reverse("tenant-invitations"), **headers)
        assert resp.status_code == status.HTTP_200_OK
        tokens = [r["token"] for r in resp.data["results"]]
        assert "tenant-b-only-token" not in tokens

    def test_tenant_isolation_member_list(self):
        """Admin of tenant A cannot see tenant B's members."""
        other_user = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_user, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )
        token = self.client.post(
            reverse("auth-login"),
            {"email": "admin1@example.com", "password": "SecurePass123"},
            format="json",
        ).data["access"]
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_TENANT_ID": str(self.tenant_a.id),
        }
        resp = self.client.get(reverse("tenant-members"), **headers)
        assert resp.status_code == status.HTTP_200_OK
        emails = [m["email"] for m in resp.data["results"]]
        assert "other@example.com" not in emails
