from rest_framework import status

from apps.core.models import Tenant
from apps.inventory.models import Product, StockBalance, StockMovement, Warehouse
from apps.accounting.models import JournalEntry, JournalEntryLine
from apps.purchases.models import PurchaseInvoice
from apps.inventory.tests.base import BaseSetup


class PurchaseInventoryTests(BaseSetup):
    def setUp(self):
        super().setUp()
        self.h = self.admin_h()
        self.make_purchase_settings(h=self.h)
        self.inv_settings = self.make_inventory_settings(h=self.h)
        self.warehouse = Warehouse.objects.get(name="Default")

    def _purchase(self, number="PUR-INV-001", lines=None, discount="0"):
        resp = self.make_purchase_draft(
            h=self.h, number=number, lines=lines, discount=discount
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        post = self.post_purchase(resp.data["id"], self.h)
        self.assertEqual(post.status_code, status.HTTP_200_OK, post.data)
        return PurchaseInvoice.objects.get(pk=resp.data["id"])

    def _line(self, product, qty="1", price="100", tax="0", desc="Item"):
        line = {
            "description": desc,
            "quantity": qty,
            "unit_price": price,
            "tax_rate": tax,
        }
        if product is not None:
            line["product_id"] = str(product.id)
        return line

    def test_purchase_posts_receipt_and_inventory_leg(self):
        product = self.make_product(sku="P-001", name="Steel")
        invoice = self._purchase(lines=[self._line(product, price="100")])
        balance = StockBalance.objects.get(
            tenant_id=self.tenant.id, product=product, warehouse=self.warehouse
        )
        self.assertEqual(float(balance.quantity), 1)
        self.assertEqual(float(balance.value), 100)
        self.assertEqual(float(balance.moving_avg_cost), 100)
        movement = StockMovement.objects.get(
            tenant_id=self.tenant.id,
            product=product,
            movement_type=StockMovement.MovementType.RECEIPT,
        )
        self.assertEqual(float(movement.quantity), 1)
        self.assertEqual(float(movement.value), 100)
        self.assertEqual(movement.purchase_invoice_id, invoice.id)
        entry = invoice.posted_journal
        lines = list(entry.lines.select_related("account"))
        by_account = {}
        for line in lines:
            by_account.setdefault(line.account.name, []).append(line)
        inventory = by_account[self.inv_settings["inventory_account_name"]]
        self.assertEqual(
            float(sum(l.debit for l in inventory)) - float(sum(l.credit for l in inventory)),
            100,
        )
        self.assertTrue(entry.is_balanced)

    def test_receipt_uses_net_after_proportional_discount(self):
        product_a = self.make_product(sku="P-A", name="A")
        product_b = self.make_product(sku="P-B", name="B")
        lines = [
            self._line(product_a, qty="1", price="60", desc="A"),
            self._line(product_b, qty="1", price="40", desc="B"),
        ]
        invoice = self._purchase(lines=lines, discount="10")
        ba = StockBalance.objects.get(product=product_a)
        bb = StockBalance.objects.get(product=product_b)
        self.assertEqual(float(ba.value), 54)
        self.assertEqual(float(ba.moving_avg_cost), 54)
        self.assertEqual(float(bb.value), 36)
        self.assertEqual(float(bb.moving_avg_cost), 36)
        entry = invoice.posted_journal
        self.assertTrue(entry.is_balanced)
        inventory_name = self.inv_settings["inventory_account_name"]
        inventory_lines = [
            l for l in entry.lines.select_related("account")
            if l.account.name == inventory_name
        ]
        self.assertEqual(
            float(sum(l.debit - l.credit for l in inventory_lines)), 90
        )

    def test_service_lines_keep_expense_leg(self):
        product = self.make_product(sku="P-001", name="Goods")
        lines = [
            self._line(product, qty="1", price="80", desc="Goods"),
            self._line(None, qty="1", price="20", desc="Shipping"),
        ]
        invoice = self._purchase(lines=lines)
        entry = invoice.posted_journal
        lines_je = list(entry.lines.select_related("account"))
        expense = [l for l in lines_je if l.account.name == "Purchases Expense"]
        inventory = [
            l for l in lines_je
            if l.account.name == self.inv_settings["inventory_account_name"]
        ]
        self.assertEqual(float(inventory[0].debit), 80)
        self.assertEqual(float(expense[0].debit), 20)
        self.assertTrue(entry.is_balanced)

    def test_purchase_with_vat_books_input_vat_on_stock(self):
        product = self.make_product(sku="P-001", name="Goods")
        invoice = self._purchase(
            lines=[self._line(product, price="100", tax="10")]
        )
        entry = invoice.posted_journal
        lines_je = list(entry.lines.select_related("account"))
        inventory = [
            l for l in lines_je
            if l.account.name == self.inv_settings["inventory_account_name"]
        ]
        vat = [l for l in lines_je if l.account.name == "Input VAT"]
        self.assertEqual(float(inventory[0].debit), 100)
        self.assertEqual(float(vat[0].debit), 10)
        bank = [l for l in lines_je if l.account.name == "Accounts Payable"]
        self.assertEqual(float(bank[0].credit), 110)
        self.assertTrue(entry.is_balanced)

    def test_missing_inventory_settings_blocks_stock_purchase(self):
        from apps.inventory.models import InventorySettings

        InventorySettings.objects.for_tenant(self.tenant).delete()
        product = self.make_product(sku="P-001")
        resp = self.make_purchase_draft(
            h=self.h, number="PUR-NOSET", lines=[self._line(product)]
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        post = self.post_purchase(resp.data["id"], self.h)
        self.assertEqual(post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not configured", post.data["detail"])
        self.assertEqual(StockMovement.objects.count(), 0)
        invoice = PurchaseInvoice.objects.get(pk=resp.data["id"])
        self.assertEqual(invoice.status, PurchaseInvoice.Status.DRAFT)

    def test_cross_tenant_product_rejected_on_purchase(self):
        other = Tenant.objects.create(name="Other Corp")
        other_product = Product.objects.create(
            tenant=other, sku="OTHR", name="Other", unit="pcs"
        )
        resp = self.make_purchase_draft(
            h=self.h,
            number="PUR-XTENANT",
            lines=[self._line(other_product)],
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_no_partial_state_on_je_reference_collision(self):
        product = self.make_product(sku="P-001")
        resp = self.make_purchase_draft(
            h=self.h, number="PUR-DUP", lines=[self._line(product)]
        )
        invoice_id = resp.data["id"]
        JournalEntry.objects.create(
            tenant_id=self.tenant.id,
            date="2026-09-01",
            description="Pre-existing",
            reference="PUR-INV-PUR-DUP",
            posted=True,
        )
        post = self.post_purchase(invoice_id, self.h)
        self.assertEqual(post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            StockMovement.objects.filter(
                tenant_id=self.tenant.id, product=product
            ).count(),
            0,
        )
        self.assertEqual(
            StockBalance.objects.filter(product=product).count(), 0
        )
        invoice = PurchaseInvoice.objects.get(pk=invoice_id)
        self.assertEqual(invoice.status, PurchaseInvoice.Status.DRAFT)

    def test_stock_quantity_lands_on_default_warehouse(self):
        product = self.make_product(sku="P-001")
        self._purchase(lines=[self._line(product, qty="5", price="20")])
        balance = StockBalance.objects.get(
            tenant_id=self.tenant.id, product=product
        )
        self.assertEqual(balance.warehouse, self.warehouse)
        self.assertEqual(float(balance.quantity), 5)
        self.assertEqual(float(balance.value), 100)