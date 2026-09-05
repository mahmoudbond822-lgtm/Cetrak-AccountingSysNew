import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.accounting.models import Account, JournalEntry
from apps.sales.models import (
    Customer,
    SalesInvoice,
    SalesInvoiceLine,
    SalesSettings,
)


def _headers(client, email="admin@example.com", password="SecurePass123", tenant=None):
    resp = client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
    )
    token = resp.data["access"]
    tid = tenant or resp.data["active_tenant"]["id"]
    return {
        "HTTP_AUTHORIZATION": f"Bearer {token}",
        "HTTP_X_TENANT_ID": str(tid),
    }


def _customer_payload(code="C-001", name="Acme Corp", email="acme@example.com"):
    return {"code": code, "name": name, "email": email}


class BaseSetup(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Corp")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        self.accountant = User.objects.create_user(
            email="accountant@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.accountant, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        self.manager = User.objects.create_user(
            email="manager@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.manager, tenant=self.tenant, role=Membership.Role.MANAGER
        )

    def admin_h(self):
        return _headers(self.client)

    def accountant_h(self):
        return _headers(self.client, email="accountant@example.com")

    def manager_h(self):
        return _headers(self.client, email="manager@example.com")

    def create_account(self, name, type_, h=None):
        h = h or self.admin_h()
        resp = self.client.post(
            reverse("account-list"),
            {"name": name, "type": type_},
            format="json",
            **h,
        )
        return resp.data

    def make_customer(self, code="C-001", name="Acme Corp", h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("customer-list"),
            _customer_payload(code, name),
            format="json",
            **h,
        ).data

    def make_settings(self, h=None):
        h = h or self.admin_h()
        ar = self.create_account("Accounts Receivable", "Asset", h)
        rev = self.create_account("Sales Revenue", "Revenue", h)
        vat = self.create_account("VAT Payable", "Liability", h)
        resp = self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": ar["id"],
                "sales_revenue": rev["id"],
                "vat_payable": vat["id"],
            },
            format="json",
            **h,
        )
        return resp.data

    def make_draft_invoice(self, h=None, number="INV-001", amount="100"):
        h = h or self.admin_h()
        customer = self.make_customer(h=h)
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": number,
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "due_date": "2026-08-15",
                "lines": [
                    {
                        "description": "Product A",
                        "quantity": "1",
                        "unit_price": amount,
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        return resp.data


class SalesPermissionsTests(BaseSetup):
    def test_admin_can_view_and_manage(self):
        resp = self.client.get(reverse("customer-list"), **self.admin_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("customer-list"), _customer_payload(), format="json", **self.admin_h()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_accountant_can_view_and_manage(self):
        resp = self.client.get(reverse("customer-list"), **self.accountant_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("customer-list"),
            _customer_payload(),
            format="json",
            **self.accountant_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_manager_can_view_but_not_manage(self):
        resp = self.client.get(reverse("customer-list"), **self.manager_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("customer-list"),
            _customer_payload(),
            format="json",
            **self.manager_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("customer-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manager_cannot_post_invoice(self):
        customer = self.make_customer(h=self.admin_h())
        h = self.manager_h()
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [
                    {"description": "A", "quantity": "1", "unit_price": "10", "tax_rate": "0"}
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_settings_admin_only(self):
        h = self.accountant_h()
        resp = self.client.get(reverse("sales-settings-detail", args=["current"]), **h)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class SalesSettingsTests(BaseSetup):
    def test_get_settings_creates_default(self):
        h = self.admin_h()
        resp = self.client.get(reverse("sales-settings-detail", args=["current"]), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["accounts_receivable"])
        self.assertIsNone(resp.data["sales_revenue"])
        self.assertIsNone(resp.data["vat_payable"])
        self.assertEqual(SalesSettings.objects.count(), 1)

    def test_put_configure_mapping(self):
        h = self.admin_h()
        data = self.make_settings(h)
        self.assertIsNotNone(data["accounts_receivable"])
        self.assertIsNotNone(data["accounts_receivable_name"])
        self.assertIsNotNone(data["sales_revenue"])
        self.assertIsNotNone(data["vat_payable"])

    def test_put_rejects_wrong_account_type(self):
        h = self.admin_h()
        asset = self.create_account("Cash", "Asset", h)
        rev = self.create_account("Sales Revenue", "Revenue", h)
        resp = self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": rev["id"],
                "sales_revenue": rev["id"],
                "vat_payable": asset["id"],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_rejects_cross_tenant_account(self):
        other = Tenant.objects.create(name="Other Corp")
        other_account = Account.objects.create(
            tenant=other, name="Ext AR", type="Asset"
        )
        h = self.admin_h()
        rev = self.create_account("Sales Revenue", "Revenue", h)
        resp = self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": str(other_account.id),
                "sales_revenue": rev["id"],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_settings_isolated_per_tenant(self):
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        h = self.admin_h()
        self.make_settings(h)
        other_h = _headers(
            self.client, email="other@example.com", tenant=other_tenant.id
        )
        resp = self.client.get(
            reverse("sales-settings-detail", args=["current"]), **other_h
        )
        self.assertIsNone(resp.data["accounts_receivable"])


class CustomerTests(BaseSetup):
    def test_create_customer(self):
        resp = self.client.post(
            reverse("customer-list"), _customer_payload(), format="json", **self.admin_h()
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)

    def test_create_customer_requires_code_and_name(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("customer-list"), {"email": "x@example.com"}, format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_code_same_tenant_idempotent(self):
        h = self.admin_h()
        first = self.client.post(
            reverse("customer-list"), _customer_payload(), format="json", **h
        )
        second = self.client.post(
            reverse("customer-list"), _customer_payload(), format="json", **h
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Customer.objects.count(), 1)

    def test_duplicate_code_other_tenant_allowed(self):
        h = self.admin_h()
        self.client.post(
            reverse("customer-list"), _customer_payload(code="C-001"), format="json", **h
        )
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other_tenant.id)
        resp = self.client.post(
            reverse("customer-list"),
            _customer_payload(code="C-001"),
            format="json",
            **other_h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 2)

    def test_list_customers_tenant_scoped(self):
        h = self.admin_h()
        self.make_customer(h=h)
        other_tenant = Tenant.objects.create(name="Other Corp")
        Customer.objects.create(
            tenant=other_tenant, code="OTHER-1", name="Other Co"
        )
        resp = self.client.get(reverse("customer-list"), **h)
        self.assertEqual(len(resp.data), 1)

    def test_update_customer(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)
        resp = self.client.patch(
            reverse("customer-detail", args=[customer["id"]]),
            {"name": "Acme Inc"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Acme Inc")

    def test_update_customer_duplicate_code_rejected(self):
        h = self.admin_h()
        a = self.make_customer(code="C-001", h=h)
        self.make_customer(code="C-002", h=h)
        resp = self.client.patch(
            reverse("customer-detail", args=[a["id"]]),
            {"code": "C-002"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_customer_without_invoices_deactivates(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)
        resp = self.client.delete(
            reverse("customer-detail", args=[customer["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        obj = Customer.objects.get(pk=customer["id"])
        self.assertFalse(obj.is_active)


class InvoiceTests(BaseSetup):
    def test_create_draft_invoice_totals(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [
                    {
                        "description": "Product A",
                        "quantity": "2",
                        "unit_price": "50",
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
        self.assertEqual(resp.data["total"], "110.0000")
        self.assertEqual(resp.data["status"], "Draft")
        self.assertEqual(len(resp.data["lines"]), 1)

    def test_create_invoice_with_discount(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "discount": "10",
                "lines": [
                    {
                        "description": "Product A",
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
        self.make_draft_invoice(h=h, number="INV-001")
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": Customer.objects.first().id,
                "invoice_date": "2026-08-02",
                "lines": [
                    {"description": "A", "quantity": "1", "unit_price": "1", "tax_rate": "0"}
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invoice_validation(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)

        def post(payload):
            return self.client.post(
                reverse("invoice-list"),
                {"number": "INV-X", "customer_id": customer["id"],
                 "invoice_date": "2026-08-01", **payload},
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
            post({"lines": [{"description": " ", "quantity": "1", "unit_price": "1"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"discount": "50", "lines": [{"description": "A", "quantity": "1", "unit_price": "10"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            post({"due_date": "2026-07-01", "lines": [{"description": "A", "quantity": "1", "unit_price": "10"}]}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_invoice_inactive_customer_rejected(self):
        h = self.admin_h()
        customer = self.make_customer(h=h)
        obj = Customer.objects.get(pk=customer["id"])
        obj.is_active = False
        obj.save()
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-100",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invoice_cross_tenant_customer_rejected(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_customer = Customer.objects.create(
            tenant=other_tenant, code="X", name="X"
        )
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-200",
                "customer_id": str(other_customer.id),
                "invoice_date": "2026-08-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invoices_filter_by_status(self):
        h = self.admin_h()
        self.make_draft_invoice(h=h, number="INV-001")
        self.make_draft_invoice(h=h, number="INV-002")
        resp = self.client.get(reverse("invoice-list") + "?status=Draft", **h)
        self.assertEqual(len(resp.data), 2)

    def test_update_draft_invoice_recomputes(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h, number="INV-001", amount="100")
        resp = self.client.patch(
            reverse("invoice-detail", args=[invoice["id"]]),
            {"discount": "20"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], "80.0000")

    def test_patch_invoice_does_not_erase_optional_fields(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h, number="INV-001")
        self.assertIsNotNone(invoice["due_date"])
        resp = self.client.patch(
            reverse("invoice-detail", args=[invoice["id"]]),
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
            reverse("invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SalesInvoice.objects.count(), 0)

    def test_invoices_tenant_scoped(self):
        h = self.admin_h()
        self.make_draft_invoice(h=h)
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_customer = Customer.objects.create(
            tenant=other_tenant, code="O1", name="O"
        )
        SalesInvoice.objects.create(
            tenant=other_tenant,
            number="OTHER-1",
            customer=other_customer,
            invoice_date="2026-08-01",
        )
        resp = self.client.get(reverse("invoice-list"), **h)
        self.assertEqual(len(resp.data), 1)


class InvoicePostingTests(BaseSetup):
    def _post(self, invoice_id, h=None):
        if h is None:
            h = self.admin_h()
        return self.client.post(
            reverse("invoice-post-invoice", args=[invoice_id]), **h
        )

    def test_post_invoice_creates_balanced_journal_entry(self):
        h = self.admin_h()
        self.make_settings(h)
        customer = self.make_customer(h=h)
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [
                    {
                        "description": "Product A",
                        "quantity": "2",
                        "unit_price": "50",
                        "tax_rate": "20",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        invoice = resp.data
        post_resp = self._post(invoice["id"], h)
        self.assertEqual(post_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(post_resp.data["status"], "Posted")
        entry = JournalEntry.objects.get(reference="SALES-INV-INV-001")
        self.assertTrue(entry.posted)
        self.assertEqual(entry.lines.count(), 3)
        debit_total = sum(line.debit for line in entry.lines.all())
        credit_total = sum(line.credit for line in entry.lines.all())
        self.assertEqual(debit_total, credit_total)
        self.assertEqual(debit_total, 120)
        obj = SalesInvoice.objects.get(pk=invoice["id"])
        self.assertIsNotNone(obj.posted_journal_id)

    def test_post_invoice_zero_tax_omits_vat_line(self):
        h = self.admin_h()
        self.make_settings(h)
        invoice = self.make_draft_invoice(h=h, number="INV-001", amount="100")
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entry = JournalEntry.objects.get(reference="SALES-INV-INV-001")
        self.assertEqual(entry.lines.count(), 2)

    def test_post_invoice_with_tax_uses_vat_account(self):
        h = self.admin_h()
        settings = self.make_settings(h)
        customer = self.make_customer(h=h)
        resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-009",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [
                    {"description": "A", "quantity": "2", "unit_price": "50", "tax_rate": "20"}
                ],
            },
            format="json",
            **h,
        )
        post = self._post(resp.data["id"], h)
        self.assertEqual(post.status_code, status.HTTP_200_OK)
        entry = JournalEntry.objects.get(reference="SALES-INV-INV-009")
        self.assertEqual(entry.lines.count(), 3)
        self.assertEqual(
            sum(l.credit for l in entry.lines.all()), 120
        )

    def test_post_invoice_without_settings_rejected(self):
        h = self.admin_h()
        invoice = self.make_draft_invoice(h=h)
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_incomplete_settings_rejected(self):
        h = self.admin_h()
        ar = self.create_account("AR", "Asset", h)
        self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {"accounts_receivable": ar["id"]},
            format="json",
            **h,
        )
        invoice = self.make_draft_invoice(h=h)
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_post_invoice_twice_rejected_and_idempotent(self):
        h = self.admin_h()
        self.make_settings(h)
        invoice = self.make_draft_invoice(h=h, number="INV-001")
        self.assertEqual(self._post(invoice["id"], h).status_code, status.HTTP_200_OK)
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            JournalEntry.objects.filter(reference="SALES-INV-INV-001").count(), 1
        )

    def test_posted_invoice_immutable(self):
        h = self.admin_h()
        self.make_settings(h)
        invoice = self.make_draft_invoice(h=h, number="INV-001")
        self._post(invoice["id"], h)
        resp = self.client.patch(
            reverse("invoice-detail", args=[invoice["id"]]),
            {"notes": "edit"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.delete(
            reverse("invoice-detail", args=[invoice["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        obj = SalesInvoice.objects.get(pk=invoice["id"])
        self.assertEqual(obj.status, SalesInvoice.Status.POSTED)

    def test_manager_cannot_post(self):
        h = self.manager_h()
        customer = self.make_customer(h=self.admin_h())
        invoice = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "lines": [{"description": "A", "quantity": "1", "unit_price": "1"}],
            },
            format="json",
            **self.admin_h(),
        ).data
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_error_gives_no_account_disclosure(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_account = Account.objects.create(
            tenant=other_tenant, name="SECRET AR", type="Asset"
        )
        SalesSettings.objects.create(
            tenant=self.tenant,
            accounts_receivable=other_account,
            sales_revenue=other_account,
        )
        invoice = self.make_draft_invoice(h=h)
        resp = self._post(invoice["id"], h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("SECRET", str(resp.data))
        self.assertEqual(JournalEntry.objects.count(), 0)


class MultiTenantIsolationTests(BaseSetup):
    def test_full_isolation_between_tenants(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_admin = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_admin, tenant=other_tenant, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other_tenant.id)

        self.make_customer(h=h)
        self.make_draft_invoice(h=h, number="INV-001")

        resp = self.client.get(reverse("customer-list"), **other_h)
        self.assertEqual(resp.data, [])
        resp = self.client.get(reverse("invoice-list"), **other_h)
        self.assertEqual(resp.data, [])

    def test_cross_tenant_object_lookup_404(self):
        h = self.admin_h()
        other_tenant = Tenant.objects.create(name="Other Corp")
        other_customer = Customer.objects.create(
            tenant=other_tenant, code="O", name="O"
        )
        other_invoice = SalesInvoice.objects.create(
            tenant=other_tenant,
            number="O-INV",
            customer=other_customer,
            invoice_date="2026-08-01",
        )
        resp = self.client.get(
            reverse("invoice-detail", args=[other_invoice.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)