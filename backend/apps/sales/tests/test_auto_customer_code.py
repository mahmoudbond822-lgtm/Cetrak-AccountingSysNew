from rest_framework.test import APITestCase

from apps.core.models import Tenant
from apps.sales.models import Customer
from apps.sales.services import CustomerService


class AutoCustomerCodeTestCase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Auto Code Tenant")
        self.service = CustomerService(self.tenant.id)

    def test_create_mints_sequential_tenant_unique_codes(self):
        one = self.service.create(name="Alpha Co")
        two = self.service.create(name="Beta Co")
        self.assertTrue(one.code)
        self.assertTrue(two.code)
        self.assertNotEqual(one.code, two.code)
        codes = list(
            Customer.objects.filter(tenant_id=self.tenant.id)
            .order_by("code")
            .values_list("code", flat=True)
        )
        self.assertEqual(len(codes), len(set(codes)))

    def test_create_mints_cus_prefixed_codes(self):
        one = self.service.create(name="First")
        self.assertTrue(one.code.startswith("CUS-"))
        self.assertEqual(one.code, "CUS-0001")
        two = self.service.create(name="Second")
        self.assertEqual(two.code, "CUS-0002")

    def test_create_with_blank_code_still_mints(self):
        customer = self.service.create(name="Blank Code", code="   ")
        self.assertTrue(customer.code)

    def test_edit_preserves_existing_code(self):
        customer = self.service.create(name="Keep Code", code="CUS-0042")
        self.assertEqual(customer.code, "CUS-0042")
        updated = self.service.update(customer.id, name="Renamed")
        self.assertEqual(updated.code, "CUS-0042")

    def test_cross_tenant_codes_reuse_sequence(self):
        other_tenant = Tenant.objects.create(name="Other Tenant")
        other = CustomerService(other_tenant.id)
        mine = self.service.create(name="A")
        theirs = other.create(name="B")
        self.assertEqual(theirs.code, mine.code)
        self.assertEqual(theirs.code, "CUS-0001")
