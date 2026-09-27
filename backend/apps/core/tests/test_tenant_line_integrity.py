"""AUD-011: line tables carry explicit, parent-derived tenant ownership."""

import uuid
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.core.models import Tenant
from apps.inventory.models import (
    Product,
    StockAdjustment,
    StockAdjustmentLine,
)
from apps.purchases.models import PurchaseInvoice, PurchaseInvoiceLine, Vendor
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine


class LineTenantOwnershipTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")

    def _account(self, tenant):
        return Account.objects.create(
            tenant=tenant, name=f"Cash {tenant.name}", type=Account.Type.ASSET
        )

    def _entry(self, tenant, reference):
        return JournalEntry.objects.create(
            tenant=tenant, date=date(2026, 1, 5), description="d", reference=reference
        )

    def _sales_invoice(self, tenant, number):
        customer = Customer.objects.create(
            tenant=tenant, code=f"C-{number}", name="Customer"
        )
        return SalesInvoice.objects.create(
            tenant=tenant,
            customer=customer,
            number=number,
            invoice_date=date(2026, 1, 5),
        )

    def _purchase_invoice(self, tenant, number):
        vendor = Vendor.objects.create(
            tenant=tenant, code=f"V-{number}", name="Vendor"
        )
        return PurchaseInvoice.objects.create(
            tenant=tenant,
            vendor=vendor,
            number=number,
            invoice_date=date(2026, 1, 5),
        )

    def _adjustment(self, tenant, number):
        return StockAdjustment.objects.create(
            tenant=tenant,
            number=number,
            adjustment_date=date(2026, 1, 5),
            reason="count",
        )

    def _product(self, tenant, sku):
        return Product.objects.create(
            tenant=tenant, sku=sku, name="Widget", unit="pcs"
        )

    def _journal_line(self, entry, **overrides):
        return JournalEntryLine.objects.create(
            entry=entry,
            account=self._account(entry.tenant),
            debit=Decimal("10.0000"),
            **overrides,
        )

    def _sales_line(self, invoice, **overrides):
        return SalesInvoiceLine.objects.create(
            invoice=invoice,
            description="Item",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("10.0000"),
            **overrides,
        )

    def _purchase_line(self, invoice, **overrides):
        return PurchaseInvoiceLine.objects.create(
            invoice=invoice,
            description="Item",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("10.0000"),
            **overrides,
        )

    def _adjustment_line(self, adjustment, **overrides):
        return StockAdjustmentLine.objects.create(
            adjustment=adjustment,
            product=self._product(adjustment.tenant, f"SKU-{adjustment.number}"),
            quantity=Decimal("2.0000"),
            **overrides,
        )

    def _line_factories(self):
        entry = self._entry(self.tenant_a, "JE-A-1")
        return [
            (JournalEntryLine, self._journal_line, entry),
            (SalesInvoiceLine, self._sales_line, self._sales_invoice(self.tenant_a, "S-1")),
            (
                PurchaseInvoiceLine,
                self._purchase_line,
                self._purchase_invoice(self.tenant_a, "P-1"),
            ),
            (
                StockAdjustmentLine,
                self._adjustment_line,
                self._adjustment(self.tenant_a, "A-1"),
            ),
        ]

    def test_line_inherits_parent_tenant(self):
        for model, factory, parent in self._line_factories():
            with self.subTest(model=model.__name__):
                line = factory(parent)
                self.assertEqual(line.tenant_id, parent.tenant_id)

    def test_explicit_matching_tenant_is_kept(self):
        for model, factory, parent in self._line_factories():
            with self.subTest(model=model.__name__):
                line = factory(parent, tenant_id=parent.tenant_id)
                self.assertEqual(line.tenant_id, parent.tenant_id)

    def test_divergent_tenant_is_rejected(self):
        for model, factory, parent in self._line_factories():
            with self.subTest(model=model.__name__):
                with self.assertRaises(ValidationError):
                    factory(parent, tenant_id=self.tenant_b.id)

    def test_full_clean_rejects_divergent_tenant(self):
        entry = self._entry(self.tenant_a, "JE-A-2")
        line = self._journal_line(entry)
        line.tenant_id = self.tenant_b.id
        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_for_tenant_scopes_lines(self):
        entry_a = self._entry(self.tenant_a, "JE-A-3")
        entry_b = self._entry(self.tenant_b, "JE-B-1")
        self._journal_line(entry_a)
        self._journal_line(entry_b)

        self.assertEqual(
            JournalEntryLine.objects.for_tenant(self.tenant_a.id).count(), 1
        )
        self.assertEqual(
            JournalEntryLine.objects.for_tenant(self.tenant_b.id).count(), 1
        )
        self.assertEqual(
            set(JournalEntryLine.objects.for_tenant(self.tenant_a.id).values_list("entry_id", flat=True)),
            {entry_a.id},
        )

    def test_tenant_is_not_nullable(self):
        entry = self._entry(self.tenant_a, "JE-A-4")
        account = self._account(self.tenant_a)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalEntryLine.objects.bulk_create(
                    [
                        JournalEntryLine(
                            id=uuid.uuid4(),
                            entry=entry,
                            account=account,
                            debit=Decimal("1.0000"),
                        )
                    ]
                )

    def test_line_does_not_leak_across_tenants_on_delete(self):
        entry_a = self._entry(self.tenant_a, "JE-A-5")
        line = self._journal_line(entry_a)
        self.assertEqual(
            JournalEntryLine.objects.for_tenant(self.tenant_b.id).filter(
                pk=line.pk
            ).count(),
            0,
        )
