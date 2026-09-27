from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from apps.sales.models import Customer, SalesInvoice
from apps.sales.tests.test_payments_api import PaymentSetup


class InvoiceListPaginationTests(PaymentSetup):
    """AUD-029: invoice list must return a DRF paginated envelope."""

    def _make_posted_invoices(self, h, count, prefix="PINV"):
        invoices = []
        for i in range(count):
            invoices.append(
                self.make_posted_invoice(
                    h=h, number=f"{prefix}-{i:04d}", amount="100"
                )
            )
        return invoices

    def test_invoice_list_is_paginated_envelope(self):
        h = self.admin_h()
        self._make_posted_invoices(h, 3)
        resp = self.client.get(
            reverse("invoice-list") + "?page_size=2", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])
        second = self.client.get(
            reverse("invoice-list") + "?page_size=2&page=2", **h
        )
        self.assertEqual(len(second.data["results"]), 1)
        self.assertIsNone(second.data["next"])

    def test_invoice_list_caps_page_size_at_100(self):
        h = self.admin_h()
        customer = Customer.objects.create(
            tenant=self.tenant, code="C-CAP", name="Cap Co"
        )
        SalesInvoice.objects.bulk_create(
            [
                SalesInvoice(
                    tenant=self.tenant,
                    customer=customer,
                    number=f"CAP-{i:04d}",
                    invoice_date=date(2026, 1, 1),
                )
                for i in range(101)
            ]
        )
        resp = self.client.get(
            reverse("invoice-list") + "?page_size=1000", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 101)
        self.assertEqual(len(resp.data["results"]), 100)
        self.assertIsNotNone(resp.data["next"])

    def test_invoice_list_query_count_does_not_scale_with_rows(self):
        """N+1 guard: paid_amount/outstanding are annotated, not computed per row."""
        h = self.admin_h()
        self._make_posted_invoices(h, 1)
        with CaptureQueriesContext(connection) as ctx:
            first = self.client.get(reverse("invoice-list"), **h)
        count_one = len(ctx.captured_queries)
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        self._make_posted_invoices(h, 4, prefix="PINV2")
        with CaptureQueriesContext(connection) as ctx:
            many = self.client.get(reverse("invoice-list"), **h)
        count_five = len(ctx.captured_queries)

        self.assertEqual(many.data["count"], 5)
        self.assertEqual(count_five, count_one)


class PaymentListPaginationTests(PaymentSetup):
    def test_payment_list_is_paginated_envelope(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PINV-PAY", amount="1000")
        cash = self.make_cash(h=h)
        self.pay(h, invoice["id"], "PAY-9001", "400", cash_account=cash)
        self.pay(h, invoice["id"], "PAY-9002", "600", cash_account=cash)
        resp = self.client.get(reverse("payment-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 2)

    def test_payment_annotation_still_reports_balances(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PINV-BAL", amount="10000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-9101", "4000", cash_account=cash)
        self.post_payment(first.data["id"], h)
        resp = self.client.get(
            reverse("payment-list"),
            {"invoice": invoice["id"], "page_size": 100},
            **h,
        )
        row = resp.data["results"][0]
        self.assertEqual(row["invoice"]["paid_amount"], "4000.0000")
        self.assertEqual(row["invoice"]["outstanding_balance"], "6000.0000")