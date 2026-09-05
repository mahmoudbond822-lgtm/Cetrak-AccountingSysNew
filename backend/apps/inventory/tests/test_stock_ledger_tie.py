from decimal import Decimal
from django.db import models, transaction

from rest_framework import status

from apps.inventory.models import (
    Product,
    StockAdjustment,
    StockAdjustmentLine,
    StockBalance,
    StockMovement,
    Warehouse,
)
from apps.inventory.services import StockAdjustmentService, StockService
from apps.accounting.models import JournalEntryLine
from apps.inventory.tests.base import BaseSetup


class StockLedgerTieTests(BaseSetup):
    """Quickstart walkthrough: after every step the invariant holds:

    balance.quantity == sum(movement.quantity)
    balance.value     == sum(movement.value) == inventory-account balance
    """

    def setUp(self):
        super().setUp()
        self.h = self.admin_h()
        self.make_purchase_settings(h=self.h)
        self.make_sales_settings(h=self.h)
        self.inv_settings = self.make_inventory_settings(h=self.h)
        self.warehouse = Warehouse.objects.get(name="Default")
        self.stock = StockService(self.tenant.id)

    def _receive(self, product, qty, cost, number):
        resp = self.make_purchase_draft(
            h=self.h,
            number=number,
            lines=[
                {
                    "product_id": str(product.id),
                    "description": "Goods in",
                    "quantity": str(qty),
                    "unit_price": str(cost),
                    "tax_rate": "0",
                }
            ],
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        post = self.post_purchase(resp.data["id"], self.h)
        self.assertEqual(post.status_code, status.HTTP_200_OK, post.data)

    def _sell(self, product, qty, price, number):
        resp = self.make_sales_draft(
            h=self.h,
            number=number,
            lines=[
                {
                    "product_id": str(product.id),
                    "description": "Goods out",
                    "quantity": str(qty),
                    "unit_price": str(price),
                    "tax_rate": "0",
                }
            ],
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        post = self.post_sales(resp.data["id"], self.h)
        self.assertEqual(post.status_code, status.HTTP_200_OK, post.data)

    def _assert_invariants(self, product):
        balance = StockBalance.objects.get(product=product)
        qty_sum = StockMovement.objects.filter(product=product).aggregate(
            total=models.Sum("quantity")
        )["total"] or Decimal("0")
        value_sum = StockMovement.objects.filter(product=product).aggregate(
            total=models.Sum("value")
        )["total"] or Decimal("0")
        self.assertEqual(balance.quantity, qty_sum)
        self.assertEqual(balance.value, value_sum)
        inventory_account_id = self.inv_settings["inventory_account"]
        ledger_value = (
            sum(
                (l.debit - l.credit)
                for l in JournalEntryLine.objects.filter(
                    account_id=inventory_account_id,
                    entry__tenant_id=self.tenant.id,
                )
            )
        )
        self.assertEqual(balance.value, ledger_value)

    def test_quickstart_walkthrough(self):
        product = Product.objects.create(
            tenant=self.tenant, sku="P-001", name="Steel Sheet", unit="pcs"
        )
        with transaction.atomic():
            self.stock._get_balance(product.id, self.warehouse.id)
        self._assert_invariants(product)
        self.assertEqual(float(product.balances.get().quantity), 0)

        self._receive(product, 10, 100, "PUR-LEDGER-1")
        balance = StockBalance.objects.get(product=product)
        self.assertEqual(float(balance.quantity), 10)
        self.assertEqual(float(balance.value), 1000)
        self.assertEqual(float(balance.moving_avg_cost), 100)
        self._assert_invariants(product)

        self._receive(product, 10, 120, "PUR-LEDGER-2")
        balance.refresh_from_db()
        self.assertEqual(float(balance.quantity), 20)
        self.assertEqual(float(balance.value), 2200)
        self.assertEqual(float(balance.moving_avg_cost), 110)
        self._assert_invariants(product)

        self._sell(product, 5, 200, "SALES-LEDGER")
        balance.refresh_from_db()
        self.assertEqual(float(balance.quantity), 15)
        self.assertEqual(float(balance.value), 1650)
        self.assertEqual(float(balance.moving_avg_cost), 110)
        self._assert_invariants(product)

        adjustment = StockAdjustment.objects.create(
            tenant=self.tenant,
            number="ADJ-LEDGER",
            adjustment_date="2026-09-06",
            reason="Count variance +2",
            status=StockAdjustment.Status.DRAFT,
        )
        StockAdjustmentLine.objects.create(
            adjustment=adjustment, product=product, quantity=Decimal("2")
        )
        StockAdjustmentService(self.tenant.id).post_adjustment(adjustment.id)
        balance.refresh_from_db()
        self.assertEqual(float(balance.quantity), 17)
        self.assertEqual(float(balance.value), 1870)
        self._assert_invariants(product)
        self.assertEqual(float(balance.moving_avg_cost), 110)