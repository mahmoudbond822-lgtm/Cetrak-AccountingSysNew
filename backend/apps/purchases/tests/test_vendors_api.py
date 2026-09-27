from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.purchases.models import Vendor

from apps.purchases.tests.base import _headers, _vendor_payload, BaseSetup


class VendorPermissionsTests(BaseSetup):
    def test_admin_can_view_and_manage(self):
        h = self.admin_h()
        resp = self.client.get(reverse("vendor-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_accountant_can_view_and_manage(self):
        h = self.accountant_h()
        resp = self.client.get(reverse("vendor-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_manager_can_view_but_not_manage(self):
        h = self.manager_h()
        resp = self.client.get(reverse("vendor-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("vendor-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class VendorCrudTests(BaseSetup):
    def test_create_vendor(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["is_active"], True)
        self.assertEqual(Vendor.objects.count(), 1)

    def test_create_vendor_requires_code_and_name(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("vendor-list"), {"tax_id": "X"}, format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_code_same_tenant_idempotent(self):
        h = self.admin_h()
        first = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        second = self.client.post(
            reverse("vendor-list"), _vendor_payload(), format="json", **h
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Vendor.objects.count(), 1)

    def test_duplicate_code_other_tenant_allowed(self):
        h = self.admin_h()
        self.client.post(
            reverse("vendor-list"), _vendor_payload(code="V-001"), format="json", **h
        )
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other_tenant.id)
        resp = self.client.post(
            reverse("vendor-list"),
            _vendor_payload(code="V-001"),
            format="json",
            **other_h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vendor.objects.count(), 2)

    def test_list_vendors_tenant_scoped(self):
        h = self.admin_h()
        self.make_vendor(h=h)
        other_tenant = Tenant.objects.create(name="Other Corp")
        Vendor.objects.create(tenant=other_tenant, code="OTHER-1", name="Other Co")
        resp = self.client.get(reverse("vendor-list"), **h)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_list_vendors_filters_inactive(self):
        h = self.admin_h()
        active = self.make_vendor(code="V-001", h=h)
        self.make_vendor(code="V-002", h=h)
        Vendor.objects.filter(pk=active["id"]).update(is_active=False)
        resp = self.client.get(
            reverse("vendor-list") + "?is_active=false", **h
        )
        self.assertEqual(len(resp.data["results"]), 1)

    def test_update_vendor(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        resp = self.client.patch(
            reverse("vendor-detail", args=[vendor["id"]]),
            {"phone": "+44 20 7946 0001"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["phone"], "+44 20 7946 0001")

    def test_update_vendor_duplicate_code_rejected(self):
        h = self.admin_h()
        a = self.make_vendor(code="V-001", h=h)
        self.make_vendor(code="V-002", h=h)
        resp = self.client.patch(
            reverse("vendor-detail", args=[a["id"]]),
            {"code": "V-002"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(resp.data))

    def test_delete_vendor_without_invoices_deactivates(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        resp = self.client.delete(
            reverse("vendor-detail", args=[vendor["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        obj = Vendor.objects.get(pk=vendor["id"])
        self.assertFalse(obj.is_active)
        self.assertTrue(Vendor.objects.filter(pk=vendor["id"]).exists())

    def test_delete_vendor_with_invoices_rejected(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        self.make_draft_invoice(h=h, vendor=vendor)
        resp = self.client.delete(
            reverse("vendor-detail", args=[vendor["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        obj = Vendor.objects.get(pk=vendor["id"])
        self.assertTrue(obj.is_active)


class VendorIsolationTests(BaseSetup):
    def test_cross_tenant_vendor_lookup_404(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_vendor = Vendor.objects.create(
            tenant=other_tenant, code="O", name="O"
        )
        resp = self.client.get(
            reverse("vendor-detail", args=[other_vendor.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_vendor_id_not_disclosed(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_vendor = Vendor.objects.create(
            tenant=other_tenant, code="SECRET-CO", name="Secret Co"
        )
        resp = self.client.get(
            reverse("vendor-detail", args=[other_vendor.id]), **h
        )
        self.assertNotIn("Secret", str(resp.data))
        self.assertNotIn("SECRET-CO", str(resp.data))