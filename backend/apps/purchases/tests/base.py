from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership


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


def _vendor_payload(code="V-001", name="Alpha Supplies Ltd", tax_id="GB 123 4567 89"):
    return {"code": code, "name": name, "tax_id": tax_id}


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

    def make_vendor(self, code="V-001", name="Alpha Supplies Ltd", h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("vendor-list"),
            _vendor_payload(code, name),
            format="json",
            **h,
        ).data

    def make_customer(self, code="C-001", name="Acme Corp", h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("customer-list"),
            {"code": code, "name": name},
            format="json",
            **h,
        ).data

    def make_purchase_settings(self, h=None):
        h = h or self.admin_h()
        ap = self.create_account("Accounts Payable", "Liability", h)
        expense = self.create_account("Purchases Expense", "Expense", h)
        input_vat = self.create_account("Input VAT", "Asset", h)
        resp = self.client.put(
            reverse("purchase-settings-detail", args=["current"]),
            {
                "accounts_payable": ap["id"],
                "expense_account": expense["id"],
                "input_vat": input_vat["id"],
            },
            format="json",
            **h,
        )
        return resp.data

    def make_sales_settings(self, h=None):
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

    def make_draft_invoice(self, h=None, number="PUR-2026-001", amount="100",
                           vendor=None, tax_rate="0", discount="0"):
        h = h or self.admin_h()
        vendor = vendor or self.make_vendor(h=h)
        resp = self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": number,
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "due_date": "2026-10-01",
                "discount": discount,
                "lines": [
                    {
                        "description": "Steel beams",
                        "quantity": "1",
                        "unit_price": amount,
                        "tax_rate": tax_rate,
                    }
                ],
            },
            format="json",
            **h,
        )
        return resp.data

    def post_invoice(self, invoice_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("purchase-invoice-post-invoice", args=[invoice_id]), **h
        )

    def make_posted_invoice(self, h=None, number="PUR-2026-001", amount="100",
                            tax_rate="0", discount="0"):
        h = h or self.admin_h()
        self.make_purchase_settings(h)
        invoice = self.make_draft_invoice(
            h=h, number=number, amount=amount, tax_rate=tax_rate, discount=discount
        )
        resp = self.post_invoice(invoice["id"], h)
        assert resp.status_code == status.HTTP_200_OK, resp.data
        return self.client.get(
            reverse("purchase-invoice-detail", args=[invoice["id"]]), **h
        ).data

    def make_cash(self, h=None, name="Cash"):
        h = h or self.admin_h()
        return self.create_account(name, "Asset", h)

    def pay(self, h, purchase_invoice_id, number, amount=None,
            cash_account=None, method="Cash", payment_date="2026-09-05", **extra):
        cash = cash_account or self.make_cash(h=h)
        cash_id = cash["id"] if isinstance(cash, dict) else str(cash)
        payload = {
            "number": number,
            "purchase_invoice_id": purchase_invoice_id,
            "payment_date": payment_date,
            "method": method,
            "cash_account": cash_id,
        }
        if amount is not None:
            payload["amount"] = str(amount)
        payload.update(extra)
        return self.client.post(
            reverse("purchase-payment-list"), payload, format="json", **h
        )

    def post_payment(self, payment_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("purchase-payment-post-payment", args=[payment_id]), **h
        )