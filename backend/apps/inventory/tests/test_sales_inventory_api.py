import threading
from concurrent.futures import ThreadPoolExecutor

from rest_framework import status
from django.db import connection, transaction
from django.test import TransactionTestCase

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.inventory.models import (
    InventorySettings,
    Product,
    StockBalance,
    StockMovement,
    Warehouse,
)
from apps.inventory.services import StockService
from apps.accounting.models import Account, JournalEntry
from apps.sales.models import (
    Customer,
    SalesInvoice,
    SalesInvoiceLine,
    SalesSettings,
)
from apps.sales.services import SalesInvoiceService
from apps.inventory.tests.base import BaseSetup


class SalesInventoryTests(BaseSetup):
    def setUp(self):
        super().setUp()
        self.h = self.admin_h()
        self.make_purchase_settings(h=self.h)
        self.make_sales_settings(h=self.h)
        self.inv_settings = self.make_inventory_settings(h=self.h)

    def _receive(self, product, qty, unit_cost):
        warehouse = Warehouse.objects.get(name="Default")
        stock = StockService(self.tenant.id)
        with transaction.atomic():
            balance = stock._get_balance(product.id, warehouse.id)
            stock.receive(
                balance,
                qty,
                unit_cost,
                StockMovement.MovementType.RECEIPT,
            )

    def _sell(self, product, qty="1", price="100", number="SALES-INV-001"):
        resp = self.make_sales_draft(
            h=self.h,
            number=number,
            lines=[
                {
                    "product_id": str(product.id),
                    "description": "Sold goods",
                    "quantity": qty,
                    "unit_price": price,
                    "tax_rate": "0",
                }
            ],
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        post = self.post_sales(resp.data["id"], self.h)
        return resp.data["id"], post

    def test_sales_posts_issue_and_cogs_leg(self):
        product = self.make_product(sku="P-001", name="Goods")
        self._receive(product, 10, 100)
        invoice_id, post = self._sell(product, qty="5", price="200")
        self.assertEqual(post.status_code, status.HTTP_200_OK, post.data)
        balance = StockBalance.objects.get(product=product)
        self.assertEqual(float(balance.quantity), 5)
        self.assertEqual(float(balance.value), 500)
        movement = StockMovement.objects.get(
            tenant_id=self.tenant.id,
            product=product,
            movement_type=StockMovement.MovementType.ISSUE,
        )
        self.assertEqual(float(movement.quantity), -5)
        self.assertEqual(float(movement.unit_cost), 100)
        self.assertEqual(float(movement.value), -500)
        self.assertEqual(str(movement.sales_invoice_id), invoice_id)
        invoice = SalesInvoice.objects.get(pk=invoice_id)
        entry = invoice.posted_journal
        self.assertTrue(entry.is_balanced)
        lines = list(entry.lines.select_related("account"))
        cogs = [
            l for l in lines if l.account.name == "Cost of Goods Sold"
        ]
        inv = [
            l for l in lines
            if l.account.name == self.inv_settings["inventory_account_name"]
        ]
        self.assertEqual(float(cogs[0].debit), 500)
        self.assertEqual(float(inv[0].credit), 500)

    def test_weighted_average_arithmetic(self):
        product = self.make_product(sku="P-001", name="Goods")
        self._receive(product, 10, 100)
        self._receive(product, 10, 120)
        balance = StockBalance.objects.get(product=product)
        self.assertEqual(float(balance.quantity), 20)
        self.assertEqual(float(balance.value), 2200)
        self.assertEqual(float(balance.moving_avg_cost), 110)
        invoice_id, post = self._sell(product, qty="5", price="200")
        self.assertEqual(post.status_code, status.HTTP_200_OK, post.data)
        balance.refresh_from_db()
        self.assertEqual(float(balance.quantity), 15)
        self.assertEqual(float(balance.value), 1650)
        self.assertEqual(float(balance.moving_avg_cost), 110)
        invoice = SalesInvoice.objects.get(pk=invoice_id)
        cogs = [l for l in invoice.posted_journal.lines.select_related("account")
                if l.account.name == "Cost of Goods Sold"]
        self.assertEqual(float(cogs[0].debit), 550)

    def test_negative_stock_rejected_with_no_artifacts(self):
        product = self.make_product(sku="P-001", name="Goods")
        je_count_before = JournalEntry.objects.count()
        invoice_id, post = self._sell(product, qty="5", price="200")
        self.assertEqual(post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", post.data["detail"])
        self.assertEqual(
            StockMovement.objects.filter(product=product).count(), 0
        )
        self.assertEqual(
            StockBalance.objects.filter(product=product).count(), 0
        )
        self.assertEqual(JournalEntry.objects.count(), je_count_before)
        invoice = SalesInvoice.objects.get(pk=invoice_id)
        self.assertEqual(invoice.status, SalesInvoice.Status.DRAFT)
        self.assertIsNone(invoice.posted_journal)

    def test_partial_failure_rolls_back_earlier_lines(self):
        held = self.make_product(sku="P-HELD", name="Held")
        short = self.make_product(sku="P-SHORT", name="Short")
        self._receive(held, 10, 100)
        resp = self.make_sales_draft(
            h=self.h,
            number="SALES-MIX",
            lines=[
                {
                    "product_id": str(held.id),
                    "description": "In stock",
                    "quantity": "1",
                    "unit_price": "100",
                    "tax_rate": "0",
                },
                {
                    "product_id": str(short.id),
                    "description": "Not in stock",
                    "quantity": "5",
                    "unit_price": "100",
                    "tax_rate": "0",
                },
            ],
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        post = self.post_sales(resp.data["id"], self.h)
        self.assertEqual(post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            StockMovement.objects.filter(
                product=held,
                movement_type=StockMovement.MovementType.ISSUE,
            ).count(),
            0,
        )
        held_balance = StockBalance.objects.get(product=held)
        self.assertEqual(float(held_balance.quantity), 10)
        self.assertEqual(float(held_balance.value), 1000)

    def test_cannot_post_twice(self):
        product = self.make_product(sku="P-001", name="Goods")
        self._receive(product, 10, 100)
        invoice_id, post = self._sell(product, qty="1", price="100")
        self.assertEqual(post.status_code, status.HTTP_200_OK)
        second = self.post_sales(invoice_id, self.h)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("posted", second.data["detail"])

    def test_stock_movements_immutable(self):
        product = self.make_product(sku="P-001", name="Goods")
        self._receive(product, 10, 100)
        self._sell(product, qty="1", price="100")
        from django.urls import reverse

        resp = self.client.post(
            reverse("stock-movement-list"),
            {},
            format="json",
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movement = StockMovement.objects.get(
            tenant_id=self.tenant.id,
            product=product,
            movement_type=StockMovement.MovementType.ISSUE,
        )
        resp = self.client.patch(
            reverse("stock-movement-detail", args=[movement.id]),
            {"quantity": "99"},
            format="json",
            **self.h,
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ConcurrentSalesPostingTests(TransactionTestCase):
    """Two simultaneous sales postings over the same product must serialize.

    Only 5 units are in stock and both invoices try to sell 5 — exactly one
    may succeed; the other must hit the row-locked negative-stock rejection
    and the ledger must never show a negative balance.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Concurrent Corp")
        self.user = User.objects.create_user(
            email="c@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.user,
            tenant=self.tenant,
            role=Membership.Role.ADMIN,
        )
        self.product = Product.objects.create(
            tenant=self.tenant, sku="RACE-1", name="Racable", unit="pcs"
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant, code="C-1", name="Buyer"
        )
        self.warehouse = Warehouse.objects.create(
            tenant=self.tenant, name="Default", is_active=True
        )
        inv_account = Account.objects.create(
            tenant=self.tenant, name="Inventory", type="Asset"
        )
        cogs_account = Account.objects.create(
            tenant=self.tenant, name="COGS", type="Expense"
        )
        ar_account = Account.objects.create(
            tenant=self.tenant, name="AR", type="Asset"
        )
        rev_account = Account.objects.create(
            tenant=self.tenant, name="Revenue", type="Revenue"
        )
        InventorySettings.objects.create(
            tenant=self.tenant,
            inventory_account=inv_account,
            cogs_account=cogs_account,
            default_warehouse=self.warehouse,
        )
        SalesSettings.objects.create(
            tenant=self.tenant,
            accounts_receivable=ar_account,
            sales_revenue=rev_account,
        )
        stock = StockService(self.tenant.id)
        with transaction.atomic():
            balance = stock._get_balance(self.product.id, self.warehouse.id)
            stock.receive(
                balance,
                5,
                100,
                StockMovement.MovementType.RECEIPT,
            )

    def _make_draft(self, number):
        return SalesInvoice.objects.create(
            tenant_id=self.tenant.id,
            number=number,
            customer=self.customer,
            invoice_date="2026-09-01",
            due_date=None,
            status=SalesInvoice.Status.DRAFT,
            subtotal=500,
            tax=0,
            total=500,
            discount=0,
        )

    def _attempt(self, invoice_id, barrier):
        try:
            service = SalesInvoiceService(self.tenant.id)
            service.post_invoice(invoice_id)
            return "ok"
        except ValueError:
            return "insufficient"

    def test_concurrent_posting_serializes(self):
        if connection.vendor != "postgresql":
            self.skipTest(
                "Row-lock serialization only applies on PostgreSQL."
            )
        draft_a = self._make_draft("SALES-A")
        SalesInvoiceLine.objects.create(
            invoice=draft_a,
            product=self.product,
            description="A",
            quantity=5,
            unit_price=100,
            tax_rate=0,
            subtotal=500,
            tax=0,
            total=500,
        )
        draft_b = self._make_draft("SALES-B")
        SalesInvoiceLine.objects.create(
            invoice=draft_b,
            product=self.product,
            description="B",
            quantity=5,
            unit_price=100,
            tax_rate=0,
            subtotal=500,
            tax=0,
            total=500,
        )
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self._attempt, draft_a.id, barrier),
                pool.submit(self._attempt, draft_b.id, barrier),
            ]
            results = [f.result(timeout=60) for f in futures]
        self.assertEqual(sorted(results), ["insufficient", "ok"])
        balance = StockBalance.objects.get(product=self.product)
        self.assertEqual(float(balance.quantity), 0)
        self.assertEqual(float(balance.value), 0)
        posted = SalesInvoice.objects.filter(
            status=SalesInvoice.Status.POSTED
        )
        self.assertEqual(posted.count(), 1)