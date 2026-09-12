from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant, AuditLog
from apps.accounts.models import User, Membership
from apps.accounts.tests import helpers as test_helpers


class UserDisableApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        self.b_admin = User.objects.create_user(
            email="badmin@example.com", password="SecurePass123"
        )

        from apps.core.models import Tenant
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        Membership.objects.create(
            user=self.admin, tenant=self.tenant_a, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant_a, role=Membership.Role.ACCOUNTANT
        )
        Membership.objects.create(
            user=self.member, tenant=self.tenant_b, role=Membership.Role.ACCOUNTANT
        )
        Membership.objects.create(
            user=self.b_admin, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )

        admin_login = test_helpers.login(self.client, "admin@example.com", "SecurePass123")
        self.admin_access = admin_login.data["access"]
        self.admin_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {self.admin_access}",
            "HTTP_X_TENANT_ID": str(self.tenant_a.id),
        }

    def _status_url(self, user_id):
        return reverse("tenant-member-status", args=[user_id])

    def _member_headers(self):
        login_resp = test_helpers.login(self.client, "member@example.com", "SecurePass123")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {login_resp.data['access']}",
            "HTTP_X_TENANT_ID": str(self.tenant_a.id),
        }

    def test_admin_can_disable_member(self):
        response = self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "Disabled"
        self.member.refresh_from_db()
        assert self.member.status == User.Status.DISABLED

    def test_non_admin_cannot_disable_member(self):
        member_headers = self._member_headers()
        response = self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **member_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_tenant_target_not_found(self):
        response = self.client.patch(
            self._status_url(self.b_admin.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_disabled_user_cannot_login(self):
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        response = test_helpers.login(self.client, "member@example.com", "SecurePass123")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_disabled_user_with_issued_access_rejected(self):
        member_headers = self._member_headers()
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        response = self.client.get(reverse("auth-me"), **member_headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_disabled_user_cannot_refresh(self):
        test_helpers.login(self.client, "member@example.com", "SecurePass123")
        assert test_helpers.refresh_cookie_value(self.client) is not None
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_disabled_user_cannot_switch_tenant(self):
        login_resp = test_helpers.login(self.client, "member@example.com", "SecurePass123")
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_b.id]),
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reenable_restores_access(self):
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        enable = self.client.patch(
            self._status_url(self.member.id),
            {"status": "Active"},
            format="json",
            **self.admin_headers,
        )
        assert enable.status_code == status.HTTP_200_OK
        self.member.refresh_from_db()
        assert self.member.status == User.Status.ACTIVE

        login_resp = test_helpers.login(self.client, "member@example.com", "SecurePass123")
        assert login_resp.status_code == status.HTTP_200_OK
        me = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        assert me.status_code == status.HTTP_200_OK

    def test_cannot_disable_last_admin(self):
        response = self.client.patch(
            self._status_url(self.admin.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "last admin" in response.data["detail"].lower()

    def test_member_status_change_audited(self):
        self.client.patch(
            self._status_url(self.member.id),
            {"status": "Disabled"},
            format="json",
            **self.admin_headers,
        )
        audit = AuditLog.objects.filter(action="member.disable").first()
        assert audit is not None
        assert str(audit.actor_id) == str(self.admin.id)
        assert audit.target_id == str(self.member.id)
        assert audit.before_data["status"] == "Active"
        assert audit.after_data["status"] == "Disabled"

    def test_me_patch_cannot_change_status(self):
        login_resp = test_helpers.login(self.client, "member@example.com", "SecurePass123")
        response = self.client.patch(
            reverse("auth-me"),
            {"status": "Disabled"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "Active"
        self.member.refresh_from_db()
        assert self.member.status == User.Status.ACTIVE