from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.core.services import TenantDecommissionService
from apps.accounts.models import User, Membership
from apps.accounts.tests.helpers import (
    login,
    post_refresh,
    refresh_cookie_value,
    tenant_id_of,
)


class BaseStatusSetup(APITestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        self.user = User.objects.create_user(
            email="user@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.user, tenant=self.tenant_a, role=Membership.Role.ADMIN
        )
        Membership.objects.create(
            user=self.user, tenant=self.tenant_b, role=Membership.Role.ADMIN
        )
        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "SecurePass123"},
            format="json",
        )
        self.token = login_resp.data["access"]

    def _account_list(self, tenant_id):
        return self.client.get(
            reverse("account-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_TENANT_ID=str(tenant_id),
        )


class UserStatusEnforcementTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Corp")
        self.user = User.objects.create_user(
            email="user@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.user, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        login_resp = self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "SecurePass123"},
            format="json",
        )
        self.token = login_resp.data["access"]
        self.tenant_id = self.tenant.id

    def test_active_user_access_allowed(self):
        response = self.client.get(
            reverse("account-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_TENANT_ID=str(self.tenant_id),
        )
        assert response.status_code == status.HTTP_200_OK

    def test_disabled_user_with_valid_access_token_rejected(self):
        self.user.status = User.Status.DISABLED
        self.user.save()
        response = self.client.get(
            reverse("account-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
            HTTP_X_TENANT_ID=str(self.tenant_id),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_disabled_user_cannot_switch_tenant(self):
        self.user.status = User.Status.DISABLED
        self.user.save()
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_id]),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_disabled_user_refresh_rejected(self):
        self.user.status = User.Status.DISABLED
        self.user.save()
        response = post_refresh(self.client)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_active_user_login_unchanged_for_active_tenant(self):
        self.user.refresh_from_db()
        assert self.user.status == User.Status.ACTIVE
        response = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        assert response.status_code == status.HTTP_200_OK


class TenantStatusEnforcementTests(BaseStatusSetup):
    def test_active_user_in_active_tenant_allowed(self):
        assert self._account_list(self.tenant_a.id).status_code == status.HTTP_200_OK

    def test_active_user_in_suspended_tenant_rejected(self):
        self.tenant_b.status = Tenant.Status.SUSPENDED
        self.tenant_b.save()
        assert self._account_list(self.tenant_b.id).status_code == status.HTTP_403_FORBIDDEN

    def test_active_user_in_cancelled_tenant_rejected(self):
        self.tenant_b.status = Tenant.Status.CANCELLED
        self.tenant_b.save()
        assert self._account_list(self.tenant_b.id).status_code == status.HTTP_403_FORBIDDEN

    def test_suspended_tenant_cannot_be_selected_during_switch(self):
        self.tenant_b.status = Tenant.Status.SUSPENDED
        self.tenant_b.save()
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_b.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cancelled_tenant_cannot_be_selected_during_switch(self):
        self.tenant_b.status = Tenant.Status.CANCELLED
        self.tenant_b.save()
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_b.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_active_tenant_can_be_selected_during_switch(self):
        response = self.client.post(
            reverse("tenant-switch", args=[self.tenant_a.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tenant"]["id"] == str(self.tenant_a.id)


class TenantBoundRefreshAfterStatusChangeTests(APITestCase):
    """AUD-012: a token bound to a retired tenant must stop minting tokens.

    A single-membership login issues a refresh token carrying ``tenant_id``. Data
    access was already denied for a non-``ACTIVE`` tenant by
    ``TenantScopedPermission``, but without a check here the token could keep
    rotating forever, which left the lock-out incomplete and burned a blacklisted
    row on every rotation.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Retiring Corp")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        login_resp = login(self.client, "admin@example.com", "SecurePass123")
        self.refresh_cookie = refresh_cookie_value(self.client)
        assert tenant_id_of(self.refresh_cookie) == str(self.tenant.id)

    def test_it_mints_nothing_for_a_suspended_tenant(self):
        self.tenant.status = Tenant.Status.SUSPENDED
        self.tenant.save(update_fields=["status"])

        response = post_refresh(self.client)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "This session's organization is no longer active."

    def test_it_mints_nothing_after_a_decommission(self):
        TenantDecommissionService.decommission(
            tenant=self.tenant,
            actor=self.admin,
            reason="Contract ended.",
        )

        response = post_refresh(self.client)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "access" not in response.data

    def test_the_denial_is_repeatable(self):
        """A refused rotation must not burn the token into a confusing state."""
        self.tenant.status = Tenant.Status.SUSPENDED
        self.tenant.save(update_fields=["status"])

        first = post_refresh(self.client)
        second = post_refresh(self.client)

        assert first.status_code == second.status_code == status.HTTP_403_FORBIDDEN

    def test_an_active_tenant_still_refreshes(self):
        response = post_refresh(self.client)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert tenant_id_of(response.data["access"]) == str(self.tenant.id)

    def test_an_unbound_refresh_is_unaffected(self):
        """Multi-tenant logins carry no ``tenant_id``; there is nothing to judge."""
        multi = Tenant.objects.create(name="Second Corp")
        Membership.objects.create(
            user=self.admin, tenant=multi, role=Membership.Role.ADMIN
        )
        fresh = APIClient()
        login(fresh, "admin@example.com", "SecurePass123")
        assert tenant_id_of(refresh_cookie_value(fresh)) is None

        response = post_refresh(fresh)

        assert response.status_code == status.HTTP_200_OK
