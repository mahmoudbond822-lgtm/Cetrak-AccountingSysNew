from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.accounting.models import Account, JournalEntry
from apps.purchases.models import PurchaseInvoice, PurchaseSettings
from apps.sales.models import Payment, SalesInvoice, Customer

from apps.purchases.tests.base import _headers, BaseSetup


class PurchasePaymentCreateTests(BaseSetup):
    def test_create_draft_payment(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        resp = self.pay(h, invoice["id"], "PAY-001", "7000", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "Draft")
        self.assertEqual(resp.data["direction"], "Payable")
        self.assertIsNone(resp.data["journal_entry_id"])
        self.assertEqual(resp.data["purchase_invoice"]["outstanding_balance"], "20000.0000")

    def test_create_payment_defaults_to_outstanding(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        resp = self.pay(h, invoice["id"], "PAY-001", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["amount"], "20000.0000")

    def test_create_rejects_draft_invoice(self):
        h = self.admin_h()
        draft = self.make_draft_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        resp = self.pay(h, draft["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.filter(
            direction=Payment.Direction.PAYABLE
        ).count(), 0)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_create_rejects_cross_tenant_invoice(self):
        h = self.admin_h()
        from apps.purchases.models import Vendor
        other = Tenant.objects.create(name="Other Corp")
        other_vendor = Vendor.objects.create(tenant=other, code="O", name="O")
        other_invoice = PurchaseInvoice.objects.create(
            tenant=other, number="O-PUR", vendor=other_vendor,
            invoice_date="2026-09-01",
        )
        cash = self.make_cash(h=h)
        resp = self.pay(h, other_invoice.id, "PAY-001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_create_rejects_overpayment(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        resp = self.pay(h, invoice["id"], "PAY-001", "20001", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())
        self.assertEqual(Payment.objects.filter(direction=Payment.Direction.PAYABLE).count(), 0)

    def test_create_rejects_zero_and_negative_amount(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        self.assertEqual(
            self.pay(h, invoice["id"], "PAY-001", "0", cash_account=cash).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.pay(h, invoice["id"], "PAY-002", "-5", cash_account=cash).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_rejects_cross_tenant_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        other = Tenant.objects.create(name="Other Corp")
        foreign_cash = Account.objects.create(
            tenant=other, name="Foreign Cash", type="Asset"
        )
        resp = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=foreign_cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_non_asset_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        rev = self.create_account("Revenue", "Revenue", h)
        resp = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=rev)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Asset", str(resp.data))

    def test_create_rejects_inactive_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        Account.objects.filter(pk=cash["id"]).update(is_active=False)
        resp = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_number_rejected(self):
        h = self.admin_h()
        invoice_a = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        invoice_b = self.make_posted_invoice(h=h, number="PUR-2026-002", amount="100")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice_a["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.pay(h, invoice_b["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(second.data))

    def test_purchase_payment_rejects_sales_invoice(self):
        h = self.admin_h()
        cash = self.make_cash(h=h)
        customer = self.make_customer(h=h)
        draft = self.client.post(
            reverse("invoice-list"),
            {
                "number": "S-INV",
                "customer_id": customer["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "100"}],
            },
            format="json",
            **h,
        )
        resp = self.pay(h, draft.data["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Payment.objects.filter(
            direction=Payment.Direction.PAYABLE
        ).count() == 0)


class PurchasePaymentPostingTests(BaseSetup):
    def test_post_payment_creates_balanced_journal_entry(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "20000", cash_account=cash)
        resp = self.post_payment(created.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "Posted")
        payment = Payment.objects.get(pk=created.data["id"])
        self.assertEqual(payment.direction, Payment.Direction.PAYABLE)
        self.assertIsNotNone(payment.journal_entry_id)
        self.assertIsNotNone(payment.posted_at)
        entry = payment.journal_entry
        self.assertTrue(entry.posted)
        self.assertEqual(entry.reference, "PAY-PUR-PUR-2026-001-PAY-001")
        self.assertEqual(entry.lines.count(), 2)
        from apps.purchases.models import PurchaseSettings
        ap_id = PurchaseSettings.objects.for_tenant(
            self.tenant.id
        ).get().accounts_payable_id
        line_map = {str(line.account_id): line for line in entry.lines.all()}
        self.assertEqual(line_map[str(ap_id)].debit, 20000)
        self.assertEqual(line_map[str(ap_id)].credit, 0)
        self.assertEqual(line_map[str(cash["id"])].credit, 20000)
        self.assertEqual(line_map[str(cash["id"])].debit, 0)
        debit_total = sum(line.debit for line in entry.lines.all())
        credit_total = sum(line.credit for line in entry.lines.all())
        self.assertEqual(debit_total, credit_total)
        invoice_resp = self.client.get(
            reverse("purchase-invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(invoice_resp.data["paid_amount"], "20000.0000")
        self.assertEqual(invoice_resp.data["outstanding_balance"], "0.0000")

    def test_partial_and_multiple_payments(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-001", "7000", cash_account=cash)
        first_post = self.post_payment(first.data["id"], h)
        self.assertEqual(first_post.status_code, status.HTTP_200_OK)
        detail = self.client.get(
            reverse("purchase-invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(detail.data["paid_amount"], "7000.0000")
        self.assertEqual(detail.data["outstanding_balance"], "13000.0000")

        second = self.pay(h, invoice["id"], "PAY-002", "13000", cash_account=cash)
        second_post = self.post_payment(second.data["id"], h)
        self.assertEqual(second_post.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_post.data["purchase_invoice"]["outstanding_balance"], "0.0000"
        )

        third = self.pay(h, invoice["id"], "PAY-003", "1", cash_account=cash)
        self.assertEqual(third.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            JournalEntry.objects.filter(
                reference__startswith="PAY-PUR-PUR-2026-001"
            ).count(),
            2,
        )

    def test_overpayment_rejected_at_post_time(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-001", "14000", cash_account=cash)
        second = self.pay(h, invoice["id"], "PAY-002", "7000", cash_account=cash)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.post_payment(first.data["id"], h)
        resp = self.post_payment(second.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(
                reference__startswith="PAY-PUR-PUR-2026-001"
            ).count(),
            1,
        )

    def test_post_payment_twice_idempotent(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(
            self.post_payment(created.data["id"], h).status_code,
            status.HTTP_200_OK,
        )
        second = self.post_payment(created.data["id"], h)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already posted", str(second.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(
                reference="PAY-PUR-PUR-2026-001-PAY-001"
            ).count(),
            1,
        )

    def test_post_payment_without_settings_rejected(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        from apps.purchases.models import PurchaseSettings
        PurchaseSettings.objects.for_tenant(self.tenant.id).update(
            accounts_payable=None
        )
        resp = self.post_payment(created.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("settings", str(resp.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-PUR").count(), 0
        )

    def test_posted_payment_immutable(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        self.post_payment(created.data["id"], h)
        resp = self.client.patch(
            reverse("purchase-payment-detail", args=[created.data["id"]]),
            {"notes": "edit"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.delete(
            reverse("purchase-payment-detail", args=[created.data["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        obj = Payment.objects.get(pk=created.data["id"])
        self.assertEqual(obj.status, Payment.Status.POSTED)

    def test_draft_editable_and_deletable(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "7000", cash_account=cash)
        resp = self.client.patch(
            reverse("purchase-payment-detail", args=[created.data["id"]]),
            {"amount": "3500"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["amount"], "3500.0000")
        self.assertEqual(resp.data["status"], "Draft")
        second = self.pay(h, invoice["id"], "PAY-002", "2000", cash_account=cash)
        resp = self.client.delete(
            reverse("purchase-payment-detail", args=[second.data["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            Payment.objects.filter(direction=Payment.Direction.PAYABLE).count(), 1
        )
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-PUR").count(), 0
        )

    def test_draft_edit_overpayment_rejected(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-001", "7000", cash_account=cash)
        resp = self.client.patch(
            reverse("purchase-payment-detail", args=[created.data["id"]]),
            {"amount": "21000"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())


class PurchasePaymentPermissionsTests(BaseSetup):
    def test_manager_can_view_but_not_manage_or_post(self):
        h = self.manager_h()
        resp = self.client.get(reverse("purchase-payment-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invoice = self.make_posted_invoice(h=self.admin_h(), number="PUR-2026-001")
        cash = self.make_cash(h=self.admin_h())
        create = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(create.status_code, status.HTTP_403_FORBIDDEN)
        draft = self.pay(
            self.admin_h(), invoice["id"], "PAY-002", "100", cash_account=cash
        )
        post = self.post_payment(draft.data["id"], h)
        self.assertEqual(post.status_code, status.HTTP_403_FORBIDDEN)

    def test_accountant_can_manage_and_post(self):
        h = self.accountant_h()
        invoice = self.make_posted_invoice(h=self.admin_h(), number="PUR-2026-001")
        cash = self.make_cash(h=self.admin_h())
        created = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        post = self.post_payment(created.data["id"], h)
        self.assertEqual(post.status_code, status.HTTP_200_OK)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("purchase-payment-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PurchasePaymentListTests(BaseSetup):
    def test_list_filters_by_status_and_invoice(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="20000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-001", "7000", cash_account=cash)
        self.pay(h, invoice["id"], "PAY-002", "13000", cash_account=cash)
        self.post_payment(first.data["id"], h)
        drafts = self.client.get(
            reverse("purchase-payment-list"), {"status": "Draft"}, **h
        )
        self.assertEqual(len(drafts.data["results"]), 1)
        posted = self.client.get(
            reverse("purchase-payment-list"), {"status": "Posted"}, **h
        )
        self.assertEqual(len(posted.data["results"]), 1)
        filtered = self.client.get(
            reverse("purchase-payment-list"),
            {"purchase_invoice": invoice["id"]},
            **h,
        )
        self.assertEqual(len(filtered.data["results"]), 2)

    def test_list_only_returns_payable_payments(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        customer = self.make_customer(h=h)
        sales_invoice = SalesInvoice.objects.create(
            tenant=self.tenant,
            number="S-DRAFT",
            customer=Customer.objects.get(pk=customer["id"]),
            invoice_date="2026-09-01",
        )
        Payment.objects.create(
            tenant=self.tenant,
            number="S-PAY",
            direction=Payment.Direction.RECEIVABLE,
            invoice=sales_invoice,
            payment_date="2026-09-05",
            amount=50,
            method=Payment.Method.CASH,
            cash_account=Account.objects.get(pk=cash["id"]),
        )
        resp = self.client.get(reverse("purchase-payment-list"), **h)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["number"], "PAY-001")

    def test_payments_tenant_scoped(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        other = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other.id)
        resp = self.client.get(reverse("purchase-payment-list"), **other_h)
        self.assertEqual(resp.data["results"], [])

    def test_cross_tenant_payment_lookup_404(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="PUR-2026-001", amount="100")
        cash = self.make_cash(h=h)
        payment = self.pay(h, invoice["id"], "PAY-001", "100", cash_account=cash)
        other = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other.id)
        resp = self.client.get(
            reverse("purchase-payment-detail", args=[payment.data["id"]]), **other_h
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class SalesPaymentCrossDirectionGuardTests(BaseSetup):
    def test_sales_receivable_payment_cannot_touch_purchase_invoice(self):
        h = self.admin_h()
        from apps.purchases.models import Vendor
        vendor = Vendor.objects.create(
            tenant=self.tenant, code="V", name="Vendor"
        )
        purchase = PurchaseInvoice.objects.create(
            tenant=self.tenant,
            number="PUR-X",
            vendor=vendor,
            invoice_date="2026-09-01",
        )
        purchase.status = PurchaseInvoice.Status.POSTED
        purchase.save()
        resp = self.client.post(
            reverse("payment-list"),
            {
                "number": "S-PAY",
                "invoice_id": str(purchase.id),
                "payment_date": "2026-09-05",
                "amount": "100",
                "method": "Cash",
                "cash_account": self.make_cash(h=h)["id"],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.count(), 0)


class PurchaseSalesLedgerCheckTests(BaseSetup):
    def test_sales_and_purchase_refs_do_not_overlap(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        self.make_sales_settings(h)
        vendor = self.make_vendor(h=h)
        customer = self.make_customer(h=h)

        sales = self.client.post(
            reverse("invoice-list"),
            {
                "number": "S-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "100"}],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("invoice-post-invoice", args=[sales.data["id"]]), **h
        )

        purchase = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "P-001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "100"}],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("purchase-invoice-post-invoice", args=[purchase.data["id"]]), **h
        )

        sales_refs = set(
            JournalEntry.objects.filter(reference__startswith="SALES-INV")
            .values_list("reference", flat=True)
        )
        purchase_refs = set(
            JournalEntry.objects.filter(reference__startswith="PUR-INV")
            .values_list("reference", flat=True)
        )
        self.assertEqual(sales_refs, {"SALES-INV-S-001"})
        self.assertEqual(purchase_refs, {"PUR-INV-P-001"})
        self.assertFalse(sales_refs & purchase_refs)

    def test_sales_receivable_je_unchanged(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        self.make_sales_settings(h)
        customer = self.make_customer(h=h)
        sales = self.client.post(
            reverse("invoice-list"),
            {
                "number": "S-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "100"}],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("invoice-post-invoice", args=[sales.data["id"]]), **h
        )
        cash = self.make_cash(h=h)
        receipt = self.client.post(
            reverse("payment-list"),
            {
                "number": "R-001",
                "invoice_id": sales.data["id"],
                "payment_date": "2026-09-05",
                "amount": "100",
                "method": "Cash",
                "cash_account": cash["id"],
            },
            format="json",
            **h,
        )
        self.assertEqual(receipt.status_code, status.HTTP_201_CREATED)
        self.client.post(
            reverse("payment-post-payment", args=[receipt.data["id"]]), **h
        )
        entry = JournalEntry.objects.get(reference="PAY-INV-S-001-R-001")
        self.assertEqual(entry.lines.count(), 2)
        self.assertTrue(entry.is_balanced)
        self.assertFalse(
            any(
                line.account_id
                == PurchaseSettings.objects.for_tenant(self.tenant.id)
                .get()
                .accounts_payable_id
                for line in entry.lines.all()
            )
        )