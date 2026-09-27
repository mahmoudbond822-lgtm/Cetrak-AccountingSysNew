from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.accounting.models import Account, JournalEntry
from apps.sales.models import Customer, Payment, SalesInvoice, SalesSettings

from apps.sales.tests.test_sales_api import _headers, _customer_payload, BaseSetup


class PaymentSetup(BaseSetup):
    def post_invoice(self, invoice_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("invoice-post-invoice", args=[invoice_id]), **h
        )

    def make_posted_invoice(self, h=None, number="INV-001", amount="100"):
        h = h or self.admin_h()
        self.make_settings(h)
        invoice = self.make_draft_invoice(h=h, number=number, amount=amount)
        resp = self.post_invoice(invoice["id"], h)
        assert resp.status_code == status.HTTP_200_OK, resp.data
        return self.client.get(
            reverse("invoice-detail", args=[invoice["id"]]), **h
        ).data

    def make_cash(self, h=None, name="Cash"):
        h = h or self.admin_h()
        return self.create_account(name, "Asset", h)

    def pay(self, h, invoice_id, number, amount, cash_account=None,
            method="Cash", payment_date="2026-09-05", **extra):
        cash = cash_account or self.make_cash(h=h)
        cash_id = cash["id"] if isinstance(cash, dict) else str(cash)
        payload = {
            "number": number,
            "invoice_id": invoice_id,
            "payment_date": payment_date,
            "amount": str(amount),
            "method": method,
            "cash_account": cash_id,
        }
        payload.update(extra)
        return self.client.post(
            reverse("payment-list"), payload, format="json", **h
        )

    def post_payment(self, payment_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("payment-post-payment", args=[payment_id]), **h
        )


class PaymentCreateTests(PaymentSetup):
    def test_create_draft_payment(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        resp = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "Draft")
        self.assertIsNone(resp.data["journal_entry_id"])
        self.assertEqual(resp.data["invoice"]["outstanding_balance"], "10000.0000")

    def test_create_rejects_draft_invoice(self):
        h = self.admin_h()
        draft = self.make_draft_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        resp = self.pay(h, draft["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_create_rejects_cross_tenant_invoice(self):
        h = self.admin_h()
        other = Tenant.objects.create(name="Other Corp")
        other_customer = Customer.objects.create(
            tenant=other, code="O", name="O"
        )
        other_invoice = SalesInvoice.objects.create(
            tenant=other, number="O-INV", customer=other_customer,
            invoice_date="2026-08-01",
        )
        cash = self.make_cash(h=h)
        resp = self.pay(h, other_invoice.id, "PAY-0001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_create_rejects_overpayment(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        resp = self.pay(h, invoice["id"], "PAY-0001", "10001", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())
        self.assertEqual(Payment.objects.count(), 0)

    def test_create_rejects_zero_and_negative_amount(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        self.assertEqual(
            self.pay(h, invoice["id"], "PAY-0001", "0", cash_account=cash).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.pay(h, invoice["id"], "PAY-0002", "-5", cash_account=cash).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_rejects_cross_tenant_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        other = Tenant.objects.create(name="Other Corp")
        foreign_cash = Account.objects.create(
            tenant=other, name="Foreign Cash", type="Asset"
        )
        resp = self.pay(
            h, invoice["id"], "PAY-0001", "100", cash_account=foreign_cash
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_non_asset_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        rev = self.create_account("Revenue", "Revenue", h)
        resp = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=rev)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Asset", str(resp.data))

    def test_create_rejects_inactive_cash_account(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        Account.objects.filter(pk=cash["id"]).update(is_active=False)
        resp = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_number_rejected(self):
        h = self.admin_h()
        invoice_a = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        invoice_b = self.make_posted_invoice(h=h, number="INV-002", amount="100")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice_a["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.pay(h, invoice_b["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(second.data))


class PaymentPostingTests(PaymentSetup):
    def test_post_payment_creates_balanced_journal_entry(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        ar = Account.objects.get(
            pk=SalesSettings.objects.for_tenant(self.tenant.id)
            .get()
            .accounts_receivable_id
        )
        created = self.pay(h, invoice["id"], "PAY-0001", "10000", cash_account=cash)
        resp = self.post_payment(created.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "Posted")
        payment = Payment.objects.get(pk=created.data["id"])
        self.assertIsNotNone(payment.journal_entry_id)
        self.assertIsNotNone(payment.posted_at)
        entry = payment.journal_entry
        self.assertTrue(entry.posted)
        self.assertEqual(entry.reference, "PAY-INV-INV-001-PAY-0001")
        self.assertEqual(entry.lines.count(), 2)
        line_map = {str(line.account_id): line for line in entry.lines.all()}
        self.assertEqual(line_map[str(cash["id"])].debit, 10000)
        self.assertEqual(line_map[str(cash["id"])].credit, 0)
        self.assertEqual(line_map[str(ar.id)].credit, 10000)
        self.assertEqual(line_map[str(ar.id)].debit, 0)
        invoice_resp = self.client.get(
            reverse("invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(invoice_resp.data["paid_amount"], "10000.0000")
        self.assertEqual(invoice_resp.data["outstanding_balance"], "0.0000")

    def test_partial_and_multiple_payments(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        first_post = self.post_payment(first.data["id"], h)
        self.assertEqual(first_post.status_code, status.HTTP_200_OK)
        detail = self.client.get(
            reverse("invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(detail.data["outstanding_balance"], "6000.0000")
        self.assertEqual(detail.data["paid_amount"], "4000.0000")

        second = self.pay(h, invoice["id"], "PAY-0002", "6000", cash_account=cash)
        second_post = self.post_payment(second.data["id"], h)
        self.assertEqual(second_post.status_code, status.HTTP_200_OK)
        self.assertEqual(second_post.data["invoice"]["outstanding_balance"], "0.0000")

        third = self.pay(h, invoice["id"], "PAY-0003", "1", cash_account=cash)
        self.assertEqual(third.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-INV-INV-001").count(),
            2,
        )

    def test_overpayment_rejected_at_post_time(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        second = self.pay(h, invoice["id"], "PAY-0002", "7000", cash_account=cash)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.post_payment(first.data["id"], h)
        resp = self.post_payment(second.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-INV-INV-001").count(),
            1,
        )

    def test_post_payment_twice_idempotent(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(
            self.post_payment(created.data["id"], h).status_code,
            status.HTTP_200_OK,
        )
        second = self.post_payment(created.data["id"], h)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already posted", str(second.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(reference="PAY-INV-INV-001-PAY-0001").count(),
            1,
        )

    def test_post_payment_without_settings_rejected(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        SalesSettings.objects.for_tenant(self.tenant.id).update(
            accounts_receivable=None
        )
        resp = self.post_payment(created.data["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("settings", str(resp.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-INV").count(), 0
        )

    def test_posted_payment_immutable(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        self.post_payment(created.data["id"], h)
        resp = self.client.patch(
            reverse("payment-detail", args=[created.data["id"]]),
            {"notes": "edit"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.delete(
            reverse("payment-detail", args=[created.data["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        obj = Payment.objects.get(pk=created.data["id"])
        self.assertEqual(obj.status, Payment.Status.POSTED)

    def test_draft_editable_and_deletable(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        resp = self.client.patch(
            reverse("payment-detail", args=[created.data["id"]]),
            {"amount": "3500"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["amount"], "3500.0000")
        self.assertEqual(resp.data["status"], "Draft")
        second = self.pay(h, invoice["id"], "PAY-0002", "2000", cash_account=cash)
        resp = self.client.delete(
            reverse("payment-detail", args=[second.data["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.filter(reference__startswith="PAY-INV").count(), 0
        )

    def test_draft_edit_overpayment_rejected(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        resp = self.client.patch(
            reverse("payment-detail", args=[created.data["id"]]),
            {"amount": "11000"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("outstanding", str(resp.data).lower())


class PaymentPermissionsTests(PaymentSetup):
    def test_manager_can_view_but_not_manage_or_post(self):
        h = self.manager_h()
        resp = self.client.get(reverse("payment-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invoice = self.make_posted_invoice(h=self.admin_h(), number="INV-001")
        cash = self.make_cash(h=self.admin_h())
        create = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(create.status_code, status.HTTP_403_FORBIDDEN)
        draft = self.pay(
            self.admin_h(), invoice["id"], "PAY-0002", "100", cash_account=cash
        )
        post = self.post_payment(draft.data["id"], h)
        self.assertEqual(post.status_code, status.HTTP_403_FORBIDDEN)

    def test_accountant_can_manage_and_post(self):
        h = self.accountant_h()
        invoice = self.make_posted_invoice(h=self.admin_h(), number="INV-001")
        cash = self.make_cash(h=self.admin_h())
        created = self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        post = self.post_payment(created.data["id"], h)
        self.assertEqual(post.status_code, status.HTTP_200_OK)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("payment-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentListTests(PaymentSetup):
    def test_list_filters_by_status_and_invoice(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        first = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        self.pay(h, invoice["id"], "PAY-0002", "6000", cash_account=cash)
        self.post_payment(first.data["id"], h)
        drafts = self.client.get(
            reverse("payment-list"), {"status": "Draft"}, **h
        )
        self.assertEqual(len(drafts.data["results"]), 1)
        posted = self.client.get(
            reverse("payment-list"), {"status": "Posted"}, **h
        )
        self.assertEqual(len(posted.data["results"]), 1)
        filtered = self.client.get(
            reverse("payment-list"), {"invoice": invoice["id"]}, **h
        )
        self.assertEqual(len(filtered.data["results"]), 2)

    def test_payments_tenant_scoped(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="100")
        cash = self.make_cash(h=h)
        self.pay(h, invoice["id"], "PAY-0001", "100", cash_account=cash)
        other = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other, role=Membership.Role.ADMIN
        )
        other_h = _headers(
            self.client, email="other@example.com", tenant=other.id
        )
        resp = self.client.get(reverse("payment-list"), **other_h)
        self.assertEqual(resp.data["results"], [])

    def test_invoice_serializer_exposes_balance_fields(self):
        h = self.admin_h()
        invoice = self.make_posted_invoice(h=h, number="INV-001", amount="10000")
        cash = self.make_cash(h=h)
        created = self.pay(h, invoice["id"], "PAY-0001", "4000", cash_account=cash)
        self.post_payment(created.data["id"], h)
        row = self.client.get(
            reverse("invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(row.data["paid_amount"], "4000.0000")
        self.assertEqual(row.data["outstanding_balance"], "6000.0000")