from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.core.models import Tenant
from apps.purchases.models import PurchaseInvoice, Vendor
from apps.purchases.services import PurchaseInvoiceService
from apps.purchases.tests.base import BaseSetup


def _lines(unit_price="10.00", quantity="2", tax_rate="0"):
    return [
        {
            "description": "Steel beams",
            "quantity": quantity,
            "unit_price": unit_price,
            "tax_rate": tax_rate,
        }
    ]


class AutoInvoiceNumberTestCase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Auto Number Tenant")
        self.service = PurchaseInvoiceService(self.tenant.id)
        self.vendor = Vendor.objects.create(
            tenant_id=self.tenant.id, code="V-001", name="Alpha Supplies"
        )

    def create_draft(self, number="", **overrides):
        kwargs = dict(
            number=number,
            vendor_id=self.vendor.id,
            invoice_date=date.today().isoformat(),
            due_date=None,
            discount="0",
            notes=None,
            lines_data=_lines(),
        )
        kwargs.update(overrides)
        return self.service.create_draft(**kwargs)

    def test_create_mints_sequential_tenant_unique_numbers(self):
        one = self.create_draft()
        two = self.create_draft()
        self.assertTrue(one.number)
        self.assertTrue(two.number)
        self.assertNotEqual(one.number, two.number)
        numbers = list(
            PurchaseInvoice.objects.filter(tenant_id=self.tenant.id)
            .order_by("number")
            .values_list("number", flat=True)
        )
        self.assertEqual(len(numbers), len(set(numbers)))

    def test_create_mints_inv_prefixed_numbers(self):
        one = self.create_draft()
        self.assertTrue(one.number.startswith("INV-"))
        self.assertEqual(one.number, "INV-0001")
        two = self.create_draft()
        self.assertEqual(two.number, "INV-0002")

    def test_create_with_blank_number_still_mints(self):
        invoice = self.create_draft(number="   ")
        self.assertTrue(invoice.number)

    def test_collision_skips_taken_number(self):
        self.create_draft(number="INV-0001")
        invoice = self.create_draft()
        self.assertEqual(invoice.number, "INV-0002")

    def test_manual_high_number_then_mint_continues_after_it(self):
        self.create_draft(number="INV-0005")
        invoice = self.create_draft()
        self.assertEqual(invoice.number, "INV-0006")

    def test_edit_preserves_existing_number(self):
        invoice = self.create_draft(number="INV-0042")
        self.assertEqual(invoice.number, "INV-0042")
        updated = self.service.update_draft(invoice.id, notes="Renamed")
        self.assertEqual(updated.number, "INV-0042")
        still = self.service.update_draft(invoice.id, number="INV-9999")
        self.assertEqual(still.number, "INV-0042")

    def test_cross_tenant_numbers_use_independent_sequences(self):
        other_tenant = Tenant.objects.create(name="Other Tenant")
        other = PurchaseInvoiceService(other_tenant.id)
        other_vendor = Vendor.objects.create(
            tenant_id=other_tenant.id, code="V-001", name="Other Supplies"
        )
        my_invoice = self.create_draft()
        their_invoice = other.create_draft(
            number="",
            vendor_id=other_vendor.id,
            invoice_date=date.today().isoformat(),
            due_date=None,
            discount="0",
            notes=None,
            lines_data=_lines(),
        )
        self.assertEqual(their_invoice.number, my_invoice.number)
        self.assertEqual(their_invoice.number, "INV-0001")

    def test_explicit_duplicate_number_rejected(self):
        self.create_draft(number="INV-0042")
        with self.assertRaises(ValueError):
            self.create_draft(number="INV-0042")


class AutoInvoiceNumberApiTestCase(BaseSetup):
    def test_post_without_number_mints_inv_0001(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "description": "A",
                        "quantity": "1",
                        "unit_price": "10",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["number"], "INV-0001")

    def test_second_create_gets_next_free_number(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        first = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "INV-0001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "description": "A",
                        "quantity": "1",
                        "unit_price": "10",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(first.status_code, 201, first.content)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-02",
                "lines": [
                    {
                        "description": "A",
                        "quantity": "1",
                        "unit_price": "10",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["number"], "INV-0002")

    def test_patch_ignores_submitted_number(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        created = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "INV-0001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "description": "A",
                        "quantity": "1",
                        "unit_price": "10",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(created.status_code, 201, created.content)
        resp = self.client.patch(
            reverse("purchase-invoice-detail", args=[created.data["id"]]),
            {"number": "INV-9999", "notes": "Edited"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["number"], "INV-0001")