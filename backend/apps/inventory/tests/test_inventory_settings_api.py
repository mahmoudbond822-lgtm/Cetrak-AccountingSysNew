from rest_framework import status
from django.urls import reverse

from apps.core.models import Tenant
from apps.inventory.models import InventorySettings, Warehouse, Product
from apps.accounting.models import Account
from apps.inventory.tests.base import BaseSetup


class InventorySettingsTests(BaseSetup):
    def test_get_creates_single_row_and_default_warehouse(self):
        h = self.admin_h()
        resp = self.client.get(
            reverse("inventory-settings-detail", args=["current"]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["inventory_account"])
        self.assertEqual(InventorySettings.objects.count(), 1)
        self.assertEqual(Warehouse.objects.count(), 1)
        self.assertEqual(Warehouse.objects.first().name, "Default")
        self.assertEqual(
            str(resp.data["default_warehouse"]),
            str(Warehouse.objects.first().id),
        )

    def test_settings_admin_only(self):
        resp = self.client.get(
            reverse("inventory-settings-detail", args=["current"]),
            **self.accountant_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        resp = self.client.get(
            reverse("inventory-settings-detail", args=["current"]),
            **self.manager_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_full_mapping(self):
        h = self.admin_h()
        settings = self.make_inventory_settings(h=h)
        self.assertIsNotNone(settings["inventory_account"])
        self.assertIsNotNone(settings["cogs_account"])
        self.assertIsNotNone(settings["adjustments_account"])
        self.assertIsNotNone(settings["inventory_account_name"])
        self.assertIsNotNone(settings["default_warehouse_name"])

    def test_wrong_account_type_rejected(self):
        h = self.admin_h()
        revenue = self.create_account("Sales Revenue", "Revenue", h)
        resp = self.client.put(
            reverse("inventory-settings-detail", args=["current"]),
            {"inventory_account": revenue["id"]},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_account_rejected(self):
        other = Tenant.objects.create(name="Other Corp")
        other_account = Account.objects.create(
            tenant=other, name="Other Asset", type="Asset"
        )
        h = self.admin_h()
        resp = self.client.put(
            reverse("inventory-settings-detail", args=["current"]),
            {"inventory_account": str(other_account.id)},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_warehouse_rejected(self):
        other = Tenant.objects.create(name="Other Corp")
        other_warehouse = Warehouse.objects.create(
            tenant=other, name="Other WH"
        )
        h = self.admin_h()
        resp = self.client.put(
            reverse("inventory-settings-detail", args=["current"]),
            {"default_warehouse": str(other_warehouse.id)},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_warehouse_rejected(self):
        inactive = self.make_warehouse(name="Closed", is_active=False)
        h = self.admin_h()
        resp = self.client.put(
            reverse("inventory-settings-detail", args=["current"]),
            {"default_warehouse": str(inactive.id)},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_single_row_never_duplicated(self):
        h = self.admin_h()
        for _ in range(3):
            resp = self.client.get(
                reverse("inventory-settings-detail", args=["current"]), **h
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(InventorySettings.objects.count(), 1)