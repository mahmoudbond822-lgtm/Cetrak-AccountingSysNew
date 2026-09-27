from django.urls import reverse
from rest_framework import status

from apps.purchases.tests.base import BaseSetup


class PurchaseInvoiceListPaginationTests(BaseSetup):
    def test_purchase_invoice_list_is_paginated_envelope(self):
        h = self.admin_h()
        for i in range(3):
            self.make_draft_invoice(h=h, number=f"PUR-2026-00{i + 1}")
        resp = self.client.get(
            reverse("purchase-invoice-list") + "?page_size=2", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])


class PurchasePaymentListPaginationTests(BaseSetup):
    def test_purchase_payment_list_is_paginated_envelope(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-100", amount="2000")
        cash = self.make_cash(h=h)
        self.pay(h, invoice["id"], "PAY-1001", "800", cash_account=cash)
        self.pay(h, invoice["id"], "PAY-1002", "1200", cash_account=cash)
        resp = self.client.get(
            reverse("purchase-payment-list") + "?page_size=1", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(len(resp.data["results"]), 1)