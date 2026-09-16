from rest_framework.test import APITestCase

from apps.core.models import Tenant
from apps.purchases.models import Vendor
from apps.purchases.services import VendorService


class AutoVendorCodeTestCase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Auto Code Tenant")
        self.service = VendorService(self.tenant.id)

    def test_create_mints_sequential_tenant_unique_codes(self):
        one = self.service.create(name="Alpha Supplies")
        two = self.service.create(name="Beta Supplies")
        self.assertTrue(one.code)
        self.assertTrue(two.code)
        self.assertNotEqual(one.code, two.code)
        codes = list(
            Vendor.objects.filter(tenant_id=self.tenant.id)
            .order_by("code")
            .values_list("code", flat=True)
        )
        self.assertEqual(len(codes), len(set(codes)))

    def test_create_mints_ven_prefixed_codes(self):
        one = self.service.create(name="First")
        self.assertTrue(one.code.startswith("VEN-"))
        self.assertEqual(one.code, "VEN-0001")
        two = self.service.create(name="Second")
        self.assertEqual(two.code, "VEN-0002")

    def test_create_with_blank_code_still_mints(self):
        vendor = self.service.create(name="Blank Code", code="   ")
        self.assertTrue(vendor.code)

    def test_edit_preserves_existing_code(self):
        vendor = self.service.create(name="Keep Code", code="VEN-0042")
        self.assertEqual(vendor.code, "VEN-0042")
        updated = self.service.update(vendor.id, name="Renamed")
        self.assertEqual(updated.code, "VEN-0042")

    def test_cross_tenant_codes_reuse_sequence(self):
        other_tenant = Tenant.objects.create(name="Other Tenant")
        other = VendorService(other_tenant.id)
        mine = self.service.create(name="A")
        theirs = other.create(name="B")
        self.assertEqual(theirs.code, mine.code)
        self.assertEqual(theirs.code, "VEN-0001")

    def test_stale_preview_gets_next_free_code(self):
        self.service.create(name="Rival", code="VEN-0001")
        vendor = self.service.create(name="Late Saver")
        self.assertEqual(vendor.code, "VEN-0002")
