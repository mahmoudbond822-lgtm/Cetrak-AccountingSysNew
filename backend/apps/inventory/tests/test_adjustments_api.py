from rest_framework import status
from django.urls import reverse
from django.db import transaction

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.inventory.models import (
    Product,
    StockAdjustment,
    StockBalance,
    StockMovement,
    Warehouse,
)
from apps.inventory.services import StockService
from apps.inventory.tests.base import BaseSetup, _headers


class AdjustmentPermissionsTests(BaseSetup):
    def test_manager_view_only(self):
        h = self.manager_h()
        resp = self.client.get(reverse("adjustment-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("adjustment-list"),
            {
                "number": "ADJ-001",
                "adjustment_date": "2026-09-05",
                "reason": "Count",
                "lines": [],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("adjustment-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class _AdjustmentBase(BaseSetup):
    def setUp(self):
        super().setUp()
        self.h = self.admin_h()
        self.inv_settings = self.make_inventory_settings(h=self.h)

    def _product(self, sku="P-001"):
        cache = getattr(self, "_adj_products", None)
        if cache is None:
            cache = self._adj_products = {}
        if sku not in cache:
            cache[sku] = self.make_product(sku=sku)
        return cache[sku]

    def _payload(self, number="ADJ-001", product_id=None, quantity="5",
                 reason="Stock count"):
        product_id = product_id or str(self._product().id)
        return {
            "number": number,
            "adjustment_date": "2026-09-05",
            "reason": reason,
            "lines": [
                {"product_id": product_id, "quantity": quantity}
            ],
        }

    def _create(self, number=None, product_id=None, quantity=None,
                reason=None):
        payload = self._payload(
            number=number or "ADJ-001",
            product_id=product_id,
            quantity=quantity if quantity is not None else "5",
            reason=reason or "Stock count",
        )
        return self.client.post(
            reverse("adjustment-list"), payload, format="json", **self.h
        )


class AdjustmentCrudTests(_AdjustmentBase):
    def test_create_and_retrieve_draft(self):
        resp = self._create()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["status"], "Draft")
        detail = self.client.get(
            reverse("adjustment-detail", args=[resp.data["id"]]), **self.h
        )
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data["lines"]), 1)

    def test_duplicate_number_rejected(self):
        self.assertEqual(self._create().status_code, status.HTTP_201_CREATED)
        resp = self._create()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StockAdjustment.objects.count(), 1)

    def test_zero_quantity_rejected(self):
        resp = self._create(quantity="0")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_product_rejected(self):
        other = Tenant.objects.create(name="Other Corp")
        other_product = Product.objects.create(
            tenant=other, sku="OTHR", name="Other", unit="pcs"
        )
        resp = self._create(product_id=str(other_product.id))
        self.assertEqual(
            resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data
        )
        self.assertEqual(StockAdjustment.objects.count(), 0)

    def test_update_draft(self):
        created = self._create().data
        resp = self.client.patch(
            reverse("adjustment-detail", args=[created["id"]]),
            {"reason": "Corrected"},
            format="json",
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["reason"], "Corrected")

    def test_delete_draft(self):
        created = self._create().data
        resp = self.client.delete(
            reverse("adjustment-detail", args=[created["id"]]), **self.h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StockAdjustment.objects.count(), 0)


class AdjustmentPostingTests(_AdjustmentBase):
    def test_post_positive_adjustment_increases_stock_at_avg(self):
        product = self.make_product(sku="P-001")
        created = self._create(product_id=str(product.id)).data
        resp = self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        movement = StockMovement.objects.get(
            product=product,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
        )
        self.assertEqual(float(movement.quantity), 5)
        self.assertEqual(float(movement.unit_cost), 0)
        balance = StockBalance.objects.get(product=product)
        self.assertEqual(float(balance.quantity), 5)
        adjustment = StockAdjustment.objects.get(pk=created["id"])
        self.assertEqual(adjustment.status, StockAdjustment.Status.POSTED)
        self.assertIsNotNone(adjustment.posted_journal)
        self.assertTrue(adjustment.posted_journal.is_balanced)

    def test_post_negative_adjustment_reduces_stock(self):
        product = self.make_product(sku="P-001")
        warehouse = Warehouse.objects.get(name="Default")
        stock = StockService(self.tenant.id)
        with transaction.atomic():
            balance = stock._get_balance(product.id, warehouse.id)
            stock.receive(
                balance,
                10,
                100,
                StockMovement.MovementType.RECEIPT,
            )
        created = self._create(
            product_id=str(product.id), quantity="-3"
        ).data
        resp = self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        balance = StockBalance.objects.get(product=product)
        self.assertEqual(float(balance.quantity), 7)
        self.assertEqual(float(balance.value), 700)
        entry = StockAdjustment.objects.get(pk=created["id"]).posted_journal
        self.assertTrue(entry.is_balanced)

    def test_negative_adjustment_over_stock_rejected(self):
        product = self.make_product(sku="P-001")
        created = self._create(
            product_id=str(product.id), quantity="-3"
        ).data
        resp = self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", resp.data["detail"])
        adjustment = StockAdjustment.objects.get(pk=created["id"])
        self.assertEqual(adjustment.status, StockAdjustment.Status.DRAFT)
        self.assertIsNone(adjustment.posted_journal)
        self.assertEqual(
            StockMovement.objects.filter(
                adjustment=adjustment
            ).count(),
            0,
        )

    def test_cannot_post_twice(self):
        product = self.make_product(sku="P-001")
        created = self._create(product_id=str(product.id)).data
        first = self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_posted_adjustment_immutable(self):
        product = self.make_product(sku="P-001")
        created = self._create(product_id=str(product.id)).data
        self.client.post(
            reverse("adjustment-post-adjustment", args=[created["id"]]),
            **self.h,
        )
        resp = self.client.patch(
            reverse("adjustment-detail", args=[created["id"]]),
            {"reason": "Tamper"},
            format="json",
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.delete(
            reverse("adjustment-detail", args=[created["id"]]), **self.h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_isolation(self):
        other = Tenant.objects.create(name="Other Corp")
        other_user = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_user, tenant=other, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other)
        product = self.make_product(sku="P-001")
        created = self._create(product_id=str(product.id), number="ADJ-ISO").data
        resp = self.client.get(
            reverse("adjustment-detail", args=[created["id"]]), **other_h
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)