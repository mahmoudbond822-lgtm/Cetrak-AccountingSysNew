"""AUD-011: the tenant backfill populates historical line rows from the parent.

Each line-table migration is reverted, a legacy line row is inserted with the
pre-migration column set (so it has no tenant), the migration is re-applied, and
the row must come back carrying the parent tenant with no NULL tenants left.
"""

import uuid
from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.core.models import Tenant
from apps.inventory.models import (
    Product,
    StockAdjustment,
    StockAdjustmentLine,
)
from apps.purchases.models import (
    PurchaseInvoice,
    PurchaseInvoiceLine,
    Vendor,
)
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine


STAMP = "2026-01-01 00:00:00"
MONEY = Decimal("10.0000")


class LineTenantBackfillTests(TransactionTestCase):
    """Round-trips the four line migrations against the real schema."""

    CASES = [
        (
            "accounting",
            "0004_journalentryline_tenant_and_more",
            "0003_add_posted_fields",
        ),
        (
            "sales",
            "0005_salesinvoiceline_tenant_and_more",
            "0004_add_product_to_sales_invoiceline",
        ),
        (
            "purchases",
            "0003_purchaseinvoiceline_tenant_and_more",
            "0002_add_product_to_purchase_invoiceline",
        ),
        (
            "inventory",
            "0002_stockadjustmentline_tenant_and_more",
            "0001_initial",
        ),
    ]

    def test_legacy_lines_are_backfilled_from_their_parent(self):
        for app_label, leaf, before in self.CASES:
            with self.subTest(app=app_label):
                self._run_case(app_label, leaf, before)

    def _run_case(self, app_label, leaf, before):
        tenant = Tenant.objects.create(name=f"Backfill {app_label}")
        line_id = uuid.uuid4()

        table, columns, values, model, parent_field, parent_id = self._legacy_row(
            app_label, tenant, line_id
        )

        executor = MigrationExecutor(connection)
        executor.migrate([(app_label, before)])
        executor.loader.build_graph()

        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({', '.join(['%s'] * len(columns))})",
                values,
            )

        executor.loader.build_graph()
        executor.migrate([(app_label, leaf)])

        line = model.objects.get(pk=line_id)
        self.assertEqual(line.tenant_id, tenant.id)
        self.assertEqual(line.tenant_id, getattr(line, parent_field).tenant_id)
        self.assertEqual(model.objects.filter(tenant_id__isnull=True).count(), 0)

    def _legacy_row(self, app_label, tenant, line_id):
        """Create the parent with the real models, then describe a legacy line.

        The line columns are the ones that existed before the tenant migration,
        so the row can only be inserted while the migration is reverted.
        """

        def db_uuid(model, value):
            return model._meta.get_field("id").get_db_prep_value(value, connection)

        base = ["id", "created_at", "updated_at"]
        base_values = [
            db_uuid(JournalEntryLine, line_id),
            STAMP,
            STAMP,
        ]

        if app_label == "accounting":
            account = Account.objects.create(
                tenant=tenant, name="Cash", type=Account.Type.ASSET
            )
            entry = JournalEntry.objects.create(
                tenant=tenant,
                date=date(2026, 1, 5),
                description="legacy",
                reference=f"LEGACY-{app_label}",
            )
            return (
                "accounting_journalentryline",
                base + ["entry_id", "account_id", "debit", "credit"],
                base_values
                + [
                    db_uuid(JournalEntry, entry.id),
                    db_uuid(Account, account.id),
                    MONEY,
                    MONEY,
                ],
                JournalEntryLine,
                "entry",
                entry.id,
            )

        if app_label == "sales":
            customer = Customer.objects.create(
                tenant=tenant, code="C-1", name="Customer"
            )
            invoice = SalesInvoice.objects.create(
                tenant=tenant,
                customer=customer,
                number="LEGACY-1",
                invoice_date=date(2026, 1, 5),
            )
            return (
                "sales_invoiceline",
                base
                + [
                    "invoice_id",
                    "description",
                    "quantity",
                    "unit_price",
                    "tax_rate",
                    "subtotal",
                    "tax",
                    "total",
                ],
                base_values
                + [
                    db_uuid(SalesInvoice, invoice.id),
                    "Item",
                    Decimal("1.0000"),
                    MONEY,
                    Decimal("0.00"),
                    MONEY,
                    Decimal("0.0000"),
                    MONEY,
                ],
                SalesInvoiceLine,
                "invoice",
                invoice.id,
            )

        if app_label == "purchases":
            vendor = Vendor.objects.create(tenant=tenant, code="V-1", name="Vendor")
            invoice = PurchaseInvoice.objects.create(
                tenant=tenant,
                vendor=vendor,
                number="LEGACY-1",
                invoice_date=date(2026, 1, 5),
            )
            return (
                "purchase_invoiceline",
                base
                + [
                    "invoice_id",
                    "description",
                    "quantity",
                    "unit_price",
                    "tax_rate",
                    "subtotal",
                    "tax",
                    "total",
                ],
                base_values
                + [
                    db_uuid(PurchaseInvoice, invoice.id),
                    "Item",
                    Decimal("1.0000"),
                    MONEY,
                    Decimal("0.00"),
                    MONEY,
                    Decimal("0.0000"),
                    MONEY,
                ],
                PurchaseInvoiceLine,
                "invoice",
                invoice.id,
            )

        product = Product.objects.create(
            tenant=tenant, sku="SKU-1", name="Widget", unit="pcs"
        )
        adjustment = StockAdjustment.objects.create(
            tenant=tenant,
            number="LEGACY-1",
            adjustment_date=date(2026, 1, 5),
            reason="count",
        )
        return (
            "inventory_stockadjustmentline",
            base + ["adjustment_id", "product_id", "quantity"],
            base_values
            + [
                db_uuid(StockAdjustment, adjustment.id),
                db_uuid(Product, product.id),
                Decimal("2.0000"),
            ],
            StockAdjustmentLine,
            "adjustment",
            adjustment.id,
        )
