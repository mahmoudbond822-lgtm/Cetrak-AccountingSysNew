from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.inventory.models import Product, Warehouse


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


def _product_payload(sku="P-001", name="Steel Sheet", unit="pcs"):
    return {"sku": sku, "name": name, "unit": unit}


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

    def make_product(self, sku="P-001", name="Steel Sheet", unit="pcs",
                     is_active=True, tenant=None):
        tenant = tenant or self.tenant
        return Product.objects.create(
            tenant=tenant, sku=sku, name=name, unit=unit, is_active=is_active
        )

    def make_warehouse(self, name="Default", is_active=True, tenant=None):
        tenant = tenant or self.tenant
        return Warehouse.objects.create(
            tenant=tenant, name=name, is_active=is_active
        )

    def make_inventory_settings(self, h=None, warehouse=None):
        h = h or self.admin_h()
        inv = self.create_account("Inventory", "Asset", h)
        cogs = self.create_account("Cost of Goods Sold", "Expense", h)
        adj = self.create_account("Stock Adjustments", "Expense", h)
        payload = {
            "inventory_account": inv["id"],
            "cogs_account": cogs["id"],
            "adjustments_account": adj["id"],
        }
        if warehouse is not None:
            payload["default_warehouse"] = str(warehouse.id)
        resp = self.client.put(
            reverse("inventory-settings-detail", args=["current"]),
            payload,
            format="json",
            **h,
        )
        self.assertEqual(
            resp.status_code, status.HTTP_200_OK, resp.data
        )
        return resp.data

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
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        return resp.data

    def make_sales_settings(self, h=None):
        h = h or self.admin_h()
        ar = self.create_account("Accounts Receivable", "Asset", h)
        rev = self.create_account("Sales Revenue", "Revenue", h)
        resp = self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": ar["id"],
                "sales_revenue": rev["id"],
                "vat_payable": None,
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        return resp.data

    def make_vendor(self, h=None, code="V-001", name="Alpha Supplies Ltd"):
        h = h or self.admin_h()
        return self.client.post(
            reverse("vendor-list"),
            {"code": code, "name": name, "tax_id": "GB 123 4567 89"},
            format="json",
            **h,
        ).data

    def make_customer(self, h=None, code="C-001", name="Acme Corp"):
        h = h or self.admin_h()
        return self.client.post(
            reverse("customer-list"),
            {"code": code, "name": name},
            format="json",
            **h,
        ).data

    def make_purchase_draft(self, h=None, number="PUR-INV-001", lines=None,
                            vendor=None, discount="0", tax_rate="0"):
        h = h or self.admin_h()
        vendor = vendor or self.make_vendor(h=h)
        if lines is None:
            lines = [
                {
                    "description": "Steel beams",
                    "quantity": "1",
                    "unit_price": "100",
                    "tax_rate": tax_rate,
                }
            ]
        return self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": number,
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "due_date": "2026-10-01",
                "discount": discount,
                "lines": lines,
            },
            format="json",
            **h,
        )

    def post_purchase(self, invoice_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("purchase-invoice-post-invoice", args=[invoice_id]), **h
        )

    def make_sales_draft(self, h=None, number="SALES-INV-001", lines=None,
                         customer=None, discount="0", tax_rate="0"):
        h = h or self.admin_h()
        customer = customer or self.make_customer(h=h)
        if lines is None:
            lines = [
                {
                    "description": "Product A",
                    "quantity": "1",
                    "unit_price": "100",
                    "tax_rate": tax_rate,
                }
            ]
        return self.client.post(
            reverse("invoice-list"),
            {
                "number": number,
                "customer_id": customer["id"],
                "invoice_date": "2026-09-01",
                "due_date": "2026-09-15",
                "discount": discount,
                "lines": lines,
            },
            format="json",
            **h,
        )

    def post_sales(self, invoice_id, h=None):
        h = h or self.admin_h()
        return self.client.post(
            reverse("invoice-post-invoice", args=[invoice_id]), **h
        )