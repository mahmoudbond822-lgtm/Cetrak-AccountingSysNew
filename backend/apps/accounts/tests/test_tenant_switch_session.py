from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant, AuditLog
from apps.accounts.models import User, Membership
from apps.accounts.tests import helpers as test_helpers


class TenantSwitchSessionTests(APITestCase):
    def setUp(self):
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

        login_resp = test_helpers.login(self.client, "multi@example.com", "SecurePass123")
        self.access = login_resp.data["access"]

    def _switch(self, tenant_id, access=None):
        return self.client.post(
            reverse("tenant-switch", args=[tenant_id]),
            HTTP_AUTHORIZATION=f"Bearer {access or self.access}",
        )

    def test_multi_tenant_login_issues_unbound_refresh(self):
        assert test_helpers.tenant_id_of(self.access) is None
        assert test_helpers.refresh_cookie_value(self.client) is not None
        assert test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client)) is None

    def test_unbound_refresh_rotation_stays_unbound(self):
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert test_helpers.tenant_id_of(response.data["access"]) is None
        assert test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client)) is None

    def test_switch_issues_access_and_refresh_scoped_to_target_tenant(self):
        response = self._switch(self.tenant_b.id)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tenant"]["id"] == str(self.tenant_b.id)
        assert "refresh" not in response.data
        assert test_helpers.tenant_id_of(response.data["access"]) == str(self.tenant_b.id)
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(self.tenant_b.id)
        )

    def test_refresh_after_switch_stays_on_target_tenant(self):
        assert self._switch(self.tenant_b.id).status_code == status.HTTP_200_OK
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert test_helpers.tenant_id_of(response.data["access"]) == str(self.tenant_b.id)
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(self.tenant_b.id)
        )

    def test_repeated_refresh_after_switch_has_no_drift(self):
        assert self._switch(self.tenant_b.id).status_code == status.HTTP_200_OK
        first = test_helpers.post_refresh(self.client)
        second = test_helpers.post_refresh(self.client)
        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_200_OK
        assert test_helpers.tenant_id_of(second.data["access"]) == str(self.tenant_b.id)
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(self.tenant_b.id)
        )

    def test_switch_back_and_refresh_returns_to_original_tenant(self):
        switch_b = self._switch(self.tenant_b.id)
        assert switch_b.status_code == status.HTTP_200_OK
        back = self._switch(self.tenant_a.id, access=switch_b.data["access"])
        assert back.status_code == status.HTTP_200_OK
        assert test_helpers.tenant_id_of(back.data["access"]) == str(self.tenant_a.id)

        refreshed = test_helpers.post_refresh(self.client)
        assert test_helpers.tenant_id_of(refreshed.data["access"]) == str(self.tenant_a.id)
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(self.tenant_a.id)
        )

    def test_old_tenant_refresh_cannot_restore_previous_context(self):
        old_refresh = test_helpers.refresh_cookie_value(self.client)
        assert self._switch(self.tenant_b.id).status_code == status.HTTP_200_OK
        assert test_helpers.refresh_cookie_value(self.client) != old_refresh

        self.client.cookies["refresh_token"] = old_refresh
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_single_tenant_login_binds_refresh_and_refresh_preserves(self):
        single = User.objects.create_user(email="single@example.com", password="SecurePass123")
        single_tenant = Tenant.objects.create(name="Single Co")
        Membership.objects.create(
            user=single, tenant=single_tenant, role=Membership.Role.ADMIN
        )
        login_resp = test_helpers.login(self.client, "single@example.com", "SecurePass123")
        assert (
            test_helpers.tenant_id_of(login_resp.data["access"]) == str(single_tenant.id)
        )
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(single_tenant.id)
        )

        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert test_helpers.tenant_id_of(response.data["access"]) == str(single_tenant.id)
        assert (
            test_helpers.tenant_id_of(test_helpers.refresh_cookie_value(self.client))
            == str(single_tenant.id)
        )

    def test_switch_to_suspended_tenant_rejected(self):
        self.tenant_b.status = Tenant.Status.SUSPENDED
        self.tenant_b.save()
        response = self._switch(self.tenant_b.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_disabled_user_cannot_switch(self):
        self.user.status = User.Status.DISABLED
        self.user.save()
        response = self._switch(self.tenant_b.id)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_switch_audited_with_source_and_target(self):
        switch_b = self._switch(self.tenant_b.id)
        assert switch_b.status_code == status.HTTP_200_OK
        back = self._switch(self.tenant_a.id, access=switch_b.data["access"])
        assert back.status_code == status.HTTP_200_OK

        audit = AuditLog.objects.filter(action="tenant.switch").order_by("-created_at").first()
        assert audit is not None
        assert str(audit.actor_id) == str(self.user.id)
        assert audit.before_data["from_tenant_id"] == str(self.tenant_b.id)
        assert audit.after_data["to_tenant_id"] == str(self.tenant_a.id)
        assert str(audit.tenant_id) == str(self.tenant_a.id)

    def test_switch_no_membership_rejected(self):
        other = Tenant.objects.create(name="Other")
        response = self._switch(other.id)
        assert response.status_code == status.HTTP_404_NOT_FOUND