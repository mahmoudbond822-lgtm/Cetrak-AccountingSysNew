from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Invitation, Membership, User
from apps.accounts.tests.test_team_api import _admin_headers
from apps.core.models import Tenant


class TeamListPaginationTests(APITestCase):
    """AUD-029: team lists are real DRF pages and honor a client page size."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Corp")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        for email in ("a@example.com", "b@example.com"):
            user = User.objects.create_user(
                email=email, password="SecurePass123"
            )
            Membership.objects.create(
                user=user, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
            )
        self.headers = _admin_headers(self.client)

    def _make_invitation(self, email, token):
        return Invitation.objects.create(
            email=email,
            role=Invitation.Role.ACCOUNTANT,
            token=token,
            tenant=self.tenant,
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_member_list_returns_paginated_envelope(self):
        resp = self.client.get(
            reverse("tenant-members") + "?page_size=2", **self.headers
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])

    def test_invitation_list_honors_page_size(self):
        self._make_invitation("one@example.com", "token-one")
        self._make_invitation("two@example.com", "token-two")
        resp = self.client.get(
            reverse("tenant-invitations") + "?page_size=1", **self.headers
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertIsNotNone(resp.data["next"])
