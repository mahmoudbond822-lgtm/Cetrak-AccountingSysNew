from rest_framework import status
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounting.models import Account, JournalEntry
from apps.purchases.models import PurchaseInvoice, PurchaseSettings

from apps.purchases.tests.base import BaseSetup


class PurchaseInvoiceCreateTests(BaseSetup):
    def test_create_draft_invoice_totals(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-2026-001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "description": "Steel beams",
                        "quantity": "10",
                        "unit_price": "1000",
                        "tax_rate": "15",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["subtotal"], "10000.0000")
        self.assertEqual(resp.data["tax"], "1500.0000")
        self.assertEqual(resp.data["total"], "11500.0000")
        self.assertEqual(resp.data["status"], "Draft")
        self.assertEqual(resp.data["paid_amount"], "0.0000")
        self.assertEqual(resp.data["outstanding_balance"], "11500.0000")
        self.assertEqual(len(resp.data["lines"]), 1)

    def test_create_invoice_with_discount(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-2026-001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "discount": "10",
                "lines": [
                    {
                        "description": "Steel beams",
                        "quantity": "1",
                        "unit_price": "100",
                        "tax_rate": "10",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["subtotal"], "100.0000")
        self.assertEqual(resp.data["tax"], "10.0000")
        self.assertEqual(resp.data["total"], "100.0000")

    def test_create_invoice_duplicate_number_rejected(self):
        h = self.admin_h()
        self.make_draft_invoice(h=h, number="PUR-2026-001")
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-2026-001",
                "vendor_id": self.make_vendor(h=h)["id"],
                "invoice_date": "2026-09-02",
                "lines": [
                    {"description": "A", "quantity": "1", "unit_price": "1", "tax_rate": "0"}
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("number already exists", str(resp.data))

    def test_create_invoice_validation(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)

        def post(payload):
            return self.client.post(
                reverse("purchase-invoice-list"),
                {"number": "PUR-X", "vendor_id": vendor["id"],
                 "invoice_date": "2026-09-01", **payload},
                format="json",
                **h,
            )

        self.assertEqual(
            post({"lines": []}).status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(
            post({"lines": [{"description": "A", "quantity": "0", "unit_price": "1"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"lines": [{"description": "A", "quantity": "1", "unit_price": "-1"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"lines": [{"description": "A", "quantity": "1", "unit_price": "1", "tax_rate": "150"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"discount": "50", "lines": [{"description": "A", "quantity": "1", "unit_price": "10"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"due_date": "2026-08-01", "lines": [{"description": "A", "quantity": "1", "unit_price": "10"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_invoice_inactive_vendor_rejected(self):
        h = self.admin_h()
        vendor = self.make_vendor(h=h)
        self.client.patch(
            reverse("vendor-detail", args=[vendor["id"]]),
            {"is_active": False},
            format="json",
            **h,
        )
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-100",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invoice_cross_tenant_vendor_rejected(self):
        h = self.admin_h()
        from apps.purchases.models import Vendor
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_vendor = Vendor.objects.create(
            tenant=other_tenant, code="X", name="X"
        )
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-200",
                "vendor_id": str(other_vendor.id),
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_draft_invoice_recomputes(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h, number="PUR-2026-001", amount="100")
        resp = self.client.patch(
            reverse("purchase-invoice-detail", args=[invoice["id"]]),
            {"discount": "20"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], "80.0000")
        self.assertEqual(resp.data["status"], "Draft")

    def test_patch_invoice_preserves_optional_fields(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h, number="PUR-2026-001")
        self.assertIsNotNone(invoice["due_date"])
        resp = self.client.patch(
            reverse("purchase-invoice-detail", args=[invoice["id"]]),
            {"notes": "Hello"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["due_date"], invoice["due_date"])
        self.assertEqual(resp.data["notes"], "Hello")

    def test_delete_draft_invoice(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h)
        resp = self.client.delete(
            reverse("purchase-invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_invoices_tenant_scoped(self):
        from apps.accounts.models import User, Membership
        from apps.purchases.models import Vendor
        from apps.purchases.tests.base import _headers

        h = self.admin_h()
        self.make_draft_invoice(h=h, number="PUR-2026-001")
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        other_vendor = Vendor.objects.create(
            tenant=other_tenant, code="O1", name="O"
        )
        PurchaseInvoice.objects.create(
            tenant=other_tenant,
            number="OTHER-1",
            vendor=other_vendor,
            invoice_date="2026-09-01",
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other_tenant.id)
        resp = self.client.get(reverse("purchase-invoice-list"), **other_h)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["number"], "OTHER-1")
        resp = self.client.get(reverse("purchase-invoice-list"), **h)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["number"], "PUR-2026-001")


class PurchaseInvoicePostingTests(BaseSetup):
    def test_post_invoice_creates_balanced_journal_entry(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        vendor = self.make_vendor(h=h)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-2026-001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "description": "Steel beams",
                        "quantity": "10",
                        "unit_price": "1000",
                        "tax_rate": "15",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        post_resp = self.post_invoice(resp.data["id"], h)
        self.assertEqual(post_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(post_resp.data["status"], "Posted")
        entry = JournalEntry.objects.get(reference="PUR-INV-PUR-2026-001")
        self.assertTrue(entry.posted)
        self.assertEqual(entry.lines.count(), 3)
        line_map = {line.account.type: line for line in entry.lines.all()}
        self.assertEqual(line_map["Liability"].credit, 11500)
        self.assertEqual(line_map["Liability"].debit, 0)
        self.assertEqual(line_map["Expense"].debit, 10000)
        self.assertEqual(line_map["Expense"].credit, 0)
        self.assertEqual(line_map["Asset"].debit, 1500)
        self.assertEqual(line_map["Asset"].credit, 0)
        debit_total = sum(line.debit for line in entry.lines.all())
        credit_total = sum(line.credit for line in entry.lines.all())
        self.assertEqual(debit_total, credit_total)
        self.assertEqual(debit_total, 11500)
        obj = PurchaseInvoice.objects.get(pk=resp.data["id"])
        self.assertIsNotNone(obj.posted_journal_id)

    def test_post_invoice_zero_tax_omits_vat_line(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        invoice = self.make_draft_invoice(h=h, number="PUR-2026-001", amount="100")
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entry = JournalEntry.objects.get(reference="PUR-INV-PUR-2026-001")
        self.assertEqual(entry.lines.count(), 2)

    def test_post_invoice_without_settings_rejected(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h)
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_incomplete_settings_rejected(self):
        h = self.admin_h()
        ap = self.create_account("AP", "Liability", h)
        self.client.put(
            reverse("purchase-settings-detail", args=["current"]),
            {"accounts_payable": ap["id"]},
            format="json",
            **h,
        )
        invoice = self.make_draft_invoice(h=h)
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_with_tax_requires_input_vat(self):
        h = self.admin_h()
        ap = self.create_account("AP", "Liability", h)
        expense = self.create_account("Purchases Expense", "Expense", h)
        self.client.put(
            reverse("purchase-settings-detail", args=["current"]),
            {"accounts_payable": ap["id"], "expense_account": expense["id"]},
            format="json",
            **h,
        )
        invoice = self.make_draft_invoice(
            h=h, number="PUR-2026-002", amount="100", tax_rate="15"
        )
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("settings", str(resp.data).lower())
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_wrong_account_type_rejected(self):
        h = self.admin_h()
        asset = self.create_account("Cash", "Asset", h)
        expense = self.create_account("Purchases Expense", "Expense", h)
        input_vat = self.create_account("Input VAT", "Asset", h)
        self.client.put(
            reverse("purchase-settings-detail", args=["current"]),
            {"accounts_payable": asset["id"], "expense_account": expense["id"],
             "input_vat": input_vat["id"]},
            format="json",
            **h,
        )
        invoice = self.make_draft_invoice(h=h)
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_twice_rejected_and_idempotent(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        invoice = self.make_draft_invoice(h=h, number="PUR-2026-001")
        self.assertEqual(self.post_invoice(invoice["id"], h).status_code,
                         status.HTTP_200_OK)
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("draft", str(resp.data).lower())
        self.assertEqual(
            JournalEntry.objects.filter(reference="PUR-INV-PUR-2026-001").count(),
            1,
        )

    def test_posted_invoice_immutable(self):
        h = self.admin_h()
        self.make_purchase_settings(h)
        invoice = self.make_draft_invoice(h=h, number="PUR-2026-001")
        self.post_invoice(invoice["id"], h)
        resp = self.client.patch(
            reverse("purchase-invoice-detail", args=[invoice["id"]]),
            {"notes": "edit"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.delete(
            reverse("purchase-invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        obj = PurchaseInvoice.objects.get(pk=invoice["id"])
        self.assertEqual(obj.status, PurchaseInvoice.Status.POSTED)

    def test_manager_cannot_post(self):
        h = self.manager_h()
        vendor = self.make_vendor(h=self.admin_h())
        invoice = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-2026-001",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **self.admin_h(),
        ).data
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_error_gives_no_account_disclosure(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_account = Account.objects.create(
            tenant=other_tenant, name="SECRET AP", type="Liability"
        )
        PurchaseSettings.objects.create(
            tenant=self.tenant,
            accounts_payable=other_account,
            expense_account=other_account,
        )
        invoice = self.make_draft_invoice(h=h)
        resp = self.post_invoice(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("SECRET", str(resp.data))
        self.assertEqual(JournalEntry.objects.count(), 0)


class PurchaseInvoiceSettingsTests(BaseSetup):
    def test_settings_admin_only(self):
        h = self.accountant_h()
        resp = self.client.get(
            reverse("purchase-settings-detail", args=["current"]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_settings_creates_default(self):
        h = self.admin_h()
        resp = self.client.get(
            reverse("purchase-settings-detail", args=["current"]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["accounts_payable"])
        self.assertIsNone(resp.data["expense_account"])
        self.assertIsNone(resp.data["input_vat"])
        self.assertEqual(PurchaseSettings.objects.count(), 1)

    def test_put_configure_mapping(self):
        h = self.admin_h()
        data = self.make_purchase_settings(h)
        self.assertIsNotNone(data["accounts_payable"])
        self.assertIsNotNone(data["accounts_payable_name"])
        self.assertIsNotNone(data["expense_account"])
        self.assertIsNotNone(data["input_vat"])

    def test_put_rejects_wrong_account_type(self):
        h = self.admin_h()
        asset = self.create_account("Cash", "Asset", h)
        expense = self.create_account("Purchases Expense", "Expense", h)
        resp = self.client.put(
            reverse("purchase-settings-detail", args=["current"]),
            {
                "accounts_payable": asset["id"],
                "expense_account": expense["id"],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Liability", str(resp.data))

    def test_settings_isolated_per_tenant(self):
        from apps.accounts.models import User, Membership
        from apps.purchases.tests.base import _headers

        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        self.make_purchase_settings(self.admin_h())
        other_h = _headers(self.client, email="other@example.com", tenant=other_tenant.id)
        resp = self.client.get(
            reverse("purchase-settings-detail", args=["current"]), **other_h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["accounts_payable"])