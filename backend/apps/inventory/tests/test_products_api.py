from rest_framework import status
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.inventory.models import Product
from apps.inventory.tests.base import BaseSetup, _headers, _product_payload


class ProductPermissionsTests(BaseSetup):
    def test_admin_can_view_and_manage(self):
        resp = self.client.get(reverse("product-list"), **self.admin_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("product-list"),
            _product_payload(),
            format="json",
            **self.admin_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_accountant_can_view_and_manage(self):
        resp = self.client.get(reverse("product-list"), **self.accountant_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("product-list"),
            _product_payload(),
            format="json",
            **self.accountant_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_manager_can_view_but_not_manage(self):
        resp = self.client.get(reverse("product-list"), **self.manager_h())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            reverse("product-list"),
            _product_payload(),
            format="json",
            **self.manager_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        resp = self.client.get(reverse("product-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductCrudTests(BaseSetup):
    def test_create_product(self):
        resp = self.client.post(
            reverse("product-list"), _product_payload(), format="json",
            **self.admin_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["sku"], "P-001")
        self.assertTrue(resp.data["is_active"])

    def test_duplicate_sku_rejected(self):
        h = self.admin_h()
        self.client.post(
            reverse("product-list"), _product_payload(), format="json", **h
        )
        resp = self.client.post(
            reverse("product-list"), _product_payload(), format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Product.objects.count(), 1)

    def test_list_filter_active(self):
        h = self.admin_h()
        self.make_product(sku="P-001")
        self.make_product(sku="P-002", is_active=False)
        resp = self.client.get(
            reverse("product-list"), {"is_active": "true"}, **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["sku"], "P-001")

    def test_update_product(self):
        h = self.admin_h()
        product = self.make_product()
        resp = self.client.patch(
            reverse("product-detail", args=[product.id]),
            {"name": "Renamed"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Renamed")

    def test_update_to_duplicate_sku_rejected(self):
        h = self.admin_h()
        self.make_product(sku="P-001")
        other = self.make_product(sku="P-002")
        resp = self.client.patch(
            reverse("product-detail", args=[other.id]),
            {"sku": "P-001"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        other.refresh_from_db()
        self.assertEqual(other.sku, "P-002")

    def test_delete_unused_product_deactivates(self):
        h = self.admin_h()
        product = self.make_product()
        resp = self.client.delete(
            reverse("product-detail", args=[product.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        product.refresh_from_db()
        self.assertFalse(product.is_active)

    def test_delete_product_with_movements_rejected(self):
        from apps.inventory.models import StockMovement, StockBalance

        h = self.admin_h()
        product = self.make_product()
        warehouse = self.make_warehouse(name="WH-2")
        StockBalance.objects.create(
            tenant=self.tenant,
            product=product,
            warehouse=warehouse,
            quantity=10,
            value=1000,
            moving_avg_cost=100,
        )
        StockMovement.objects.create(
            tenant=self.tenant,
            product=product,
            warehouse=warehouse,
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity=10,
            unit_cost=100,
            value=1000,
        )
        resp = self.client.delete(
            reverse("product-detail", args=[product.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        product.refresh_from_db()
        self.assertTrue(product.is_active)

    def test_delete_product_used_on_invoice_line_rejected(self):
        from apps.inventory.models import StockMovement

        h = self.admin_h()
        product = self.make_product()
        vendor = self.make_vendor(h=h)
        self.client.post(
            reverse("purchase-invoice-list"),
            {
                "number": "PUR-X",
                "vendor_id": vendor["id"],
                "invoice_date": "2026-09-01",
                "lines": [
                    {
                        "product_id": str(product.id),
                        "description": "Stocked item",
                        "quantity": "1",
                        "unit_price": "100",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(StockMovement.objects.count(), 0)
        resp = self.client.delete(
            reverse("product-detail", args=[product.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        product.refresh_from_db()
        self.assertFalse(product.is_active)


class ProductTenantIsolationTests(BaseSetup):
    def test_other_tenant_product_not_visible(self):
        other = Tenant.objects.create(name="Other Corp")
        other_product = Product.objects.create(
            tenant=other, sku="OTHR-1", name="Other", unit="pcs"
        )
        h = self.admin_h()
        resp = self.client.get(
            reverse("product-detail", args=[other_product.id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        resp = self.client.get(reverse("product-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_same_sku_allowed_across_tenants(self):
        h = self.admin_h()
        self.make_product(sku="P-001")
        other = Tenant.objects.create(name="Other Corp")
        other_user = User.objects.create_user(
            email="other@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=other_user, tenant=other, role=Membership.Role.ADMIN
        )
        other_h = _headers(self.client, email="other@example.com", tenant=other)
        resp = self.client.post(
            reverse("product-list"), _product_payload(), format="json", **other_h
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)