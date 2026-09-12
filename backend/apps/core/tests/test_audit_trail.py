from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant, AuditLog
from apps.core.audit import AuditService
from apps.accounts.models import User, Membership
from apps.accounting.models import Account, JournalEntry
from apps.inventory.models import (
    InventorySettings,
    Product,
    Warehouse,
    StockAdjustment,
)


def _login(client, email, password):
    resp = client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
    )
    return {
        "HTTP_AUTHORIZATION": f"Bearer {resp.data['access']}",
        "HTTP_X_TENANT_ID": resp.data["tenants"][0]["id"],
    }


class BaseAuditSetup(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Corp")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        self.h = _login(self.client, "admin@example.com", "SecurePass123")

    def create_account(self, name, account_type):
        return Account.objects.create(
            tenant=self.tenant, name=name, type=account_type
        )


class AuthenticationAuditTests(BaseAuditSetup):
    def test_register_creates_audit_record(self):
        self.client.post(
            reverse("auth-register"),
            {
                "email": "boss@example.com",
                "password": "SecurePass123",
                "company_name": "Acme",
            },
            format="json",
        )
        record = AuditLog.objects.filter(action="auth.register").first()
        assert record is not None
        user = User.objects.get(email="boss@example.com")
        assert str(record.actor_id) == str(user.id)
        assert record.tenant_id == user.memberships.first().tenant_id
        assert record.target_type == "accounts.user"
        assert str(record.target_id) == str(user.id)
        assert record.after_data["email"] == "boss@example.com"
        assert record.after_data["status"] == "Active"

    def test_register_never_persists_password(self):
        self.client.post(
            reverse("auth-register"),
            {
                "email": "boss@example.com",
                "password": "SecurePass123",
                "company_name": "Acme",
            },
            format="json",
        )
        record = AuditLog.objects.filter(action="auth.register").get()
        assert "password" not in record.after_data


class MembershipAuditTests(BaseAuditSetup):
    def test_invitation_create_audited(self):
        self.client.post(
            reverse("tenant-invitations"),
            {"email": "accountant@example.com", "role": "Accountant"},
            format="json",
            **self.h,
        )
        record = AuditLog.objects.filter(action="invitation.create").get()
        assert str(record.actor_id) == str(self.admin.id)
        assert record.tenant_id == self.tenant.id
        assert record.target_type == "accounts.invitation"
        assert record.after_data["email"] == "accountant@example.com"
        assert record.after_data["role"] == "Accountant"
        assert "token" not in record.after_data

    def test_role_change_audited_with_before_after(self):
        member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        resp = self.client.patch(
            reverse("tenant-member-role", args=[member.id]),
            {"role": "Manager"},
            format="json",
            **self.h,
        )
        assert resp.status_code == status.HTTP_200_OK
        record = AuditLog.objects.filter(action="member.role_change").get()
        assert str(record.actor_id) == str(self.admin.id)
        assert record.tenant_id == self.tenant.id
        assert record.before_data["role"] == "Accountant"
        assert record.after_data["role"] == "Manager"
        assert record.before_data["user_id"] == str(member.id)
        assert record.target_type == "accounts.membership"

    def test_member_removal_audited_with_before_snapshot(self):
        member = User.objects.create_user(
            email="member@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=member, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        resp = self.client.delete(
            reverse("tenant-member-remove", args=[member.id]), **self.h
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        record = AuditLog.objects.filter(action="member.remove").get()
        assert record.tenant_id == self.tenant.id
        assert record.before_data["user_id"] == str(member.id)
        assert record.before_data["role"] == "Accountant"
        assert record.before_data["email"] == "member@example.com"


class AccountingAuditTests(BaseAuditSetup):
    def test_account_create_audited(self):
        resp = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **self.h,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        record = AuditLog.objects.filter(action="account.create").get()
        assert str(record.actor_id) == str(self.admin.id)
        assert record.tenant_id == self.tenant.id
        assert record.target_type == "accounting.account"
        assert record.after_data["name"] == "Cash"
        assert record.after_data["type"] == "Asset"

    def test_account_deactivate_audited_with_before_after(self):
        cash = self.create_account("Cash", "Asset")
        resp = self.client.patch(
            reverse("account-detail", args=[cash.id]),
            {"is_active": False},
            format="json",
            **self.h,
        )
        assert resp.status_code == status.HTTP_200_OK
        record = AuditLog.objects.filter(action="account.deactivate").get()
        assert record.before_data["is_active"] is True
        assert record.after_data["is_active"] is False

    def test_journal_create_and_post_audited(self):
        cash = self.create_account("Cash", "Asset")
        rev = self.create_account("Rev", "Revenue")
        create_resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Balanced entry",
                "reference": "JE-001",
                "lines": [
                    {"account_id": str(cash.id), "debit": "100.0000"},
                    {"account_id": str(rev.id), "credit": "100.0000"},
                ],
            },
            format="json",
            **self.h,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        entry_id = create_resp.data["id"]

        create_record = AuditLog.objects.filter(action="journal.create").get()
        assert create_record.after_data["reference"] == "JE-001"
        assert create_record.after_data["posted"] is False
        assert len(create_record.after_data["lines"]) == 2

        post_resp = self.client.post(
            reverse("journalentry-post", args=[entry_id]), **self.h
        )
        assert post_resp.status_code == status.HTTP_200_OK
        post_record = AuditLog.objects.filter(action="journal.post").get()
        assert post_record.after_data["posted"] is True
        entry = JournalEntry.objects.get(pk=entry_id)
        assert str(post_record.target_id) == str(entry.id)


class SettingsAuditTests(BaseAuditSetup):
    def test_sales_settings_update_audited(self):
        ar = self.create_account("Accounts Receivable", "Asset")
        rev = self.create_account("Sales Revenue", "Revenue")
        vat = self.create_account("VAT Payable", "Liability")
        resp = self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": str(ar.id),
                "sales_revenue": str(rev.id),
                "vat_payable": str(vat.id),
            },
            format="json",
            **self.h,
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        record = AuditLog.objects.filter(action="settings.sales.update").get()
        assert record.tenant_id == self.tenant.id
        assert str(record.after_data["accounts_receivable_id"]) == str(ar.id)
        assert str(record.after_data["sales_revenue_id"]) == str(rev.id)
        assert str(record.after_data["vat_payable_id"]) == str(vat.id)


class FinancialDocumentAuditTests(BaseAuditSetup):
    def test_sales_invoice_create_and_post_audited(self):
        ar = self.create_account("Accounts Receivable", "Asset")
        rev = self.create_account("Sales Revenue", "Revenue")
        self.client.put(
            reverse("sales-settings-detail", args=["current"]),
            {
                "accounts_receivable": str(ar.id),
                "sales_revenue": str(rev.id),
            },
            format="json",
            **self.h,
        )
        customer = self.client.post(
            reverse("customer-list"),
            {"code": "C-001", "name": "Acme Corp"},
            format="json",
            **self.h,
        ).data
        create_resp = self.client.post(
            reverse("invoice-list"),
            {
                "number": "INV-001",
                "customer_id": customer["id"],
                "invoice_date": "2026-08-01",
                "due_date": "2026-08-15",
                "lines": [
                    {
                        "description": "Product A",
                        "quantity": "1",
                        "unit_price": "100",
                        "tax_rate": "0",
                    }
                ],
            },
            format="json",
            **self.h,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        create_record = AuditLog.objects.filter(
            action="sales.invoice.create"
        ).get()
        assert create_record.after_data["number"] == "INV-001"

        post_resp = self.client.post(
            reverse("invoice-post-invoice", args=[create_resp.data["id"]]),
            **self.h,
        )
        assert post_resp.status_code == status.HTTP_200_OK, post_resp.data
        post_record = AuditLog.objects.filter(action="sales.invoice.post").get()
        assert post_record.after_data["status"] == "Posted"
        assert post_record.after_data["journal_reference"] == "SALES-INV-INV-001"

    def test_inventory_adjustment_post_audited(self):
        inv = self.create_account("Inventory", "Asset")
        adj = self.create_account("Adjustments", "Expense")
        settings = InventorySettingsServiceForTest(self.tenant)
        settings.configure(inv, adj)
        product = Product.objects.create(
            tenant=self.tenant, sku="P-001", name="Widget", unit="pcs"
        )
        create_resp = self.client.post(
            reverse("adjustment-list"),
            {
                "number": "ADJ-001",
                "adjustment_date": "2026-09-05",
                "reason": "Stock count",
                "lines": [
                    {"product_id": str(product.id), "quantity": "5"}
                ],
            },
            format="json",
            **self.h,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data
        create_record = AuditLog.objects.filter(
            action="inventory.adjustment.create"
        ).get()
        assert create_record.after_data["number"] == "ADJ-001"

        post_resp = self.client.post(
            reverse("adjustment-post-adjustment", args=[create_resp.data["id"]]),
            **self.h,
        )
        assert post_resp.status_code == status.HTTP_200_OK, post_resp.data
        post_record = AuditLog.objects.filter(
            action="inventory.adjustment.post"
        ).get()
        assert post_record.after_data["status"] == "Posted"
        assert post_record.after_data["journal_reference"] == "ADJ-INV-ADJ-001"


class InventorySettingsServiceForTest:
    def __init__(self, tenant):
        self.tenant = tenant

    def configure(self, inventory_account, adjustments_account):
        from apps.inventory.services import InventorySettingsService

        settings = InventorySettingsService(self.tenant.id).get()
        settings.inventory_account = inventory_account
        settings.adjustments_account = adjustments_account
        settings.save()
        return settings


class ImmutabilityTests(BaseAuditSetup):
    def test_audit_records_cannot_be_updated(self):
        record = AuditLog.objects.create(
            tenant_id=self.tenant.id,
            actor_id=None,
            action="test.record",
            after_data={"note": "original"},
        )
        with self.assertRaises(ValueError):
            record.after_data = {"note": "changed"}
            record.save()

    def test_audit_records_cannot_be_deleted(self):
        AuditLog.objects.create(
            tenant_id=self.tenant.id,
            actor_id=None,
            action="test.record",
        )
        with self.assertRaises(TypeError):
            AuditLog.objects.filter(action="test.record").delete()
        with self.assertRaises(TypeError):
            record = AuditLog.objects.get(action="test.record")
            record.delete()
        assert AuditLog.objects.filter(action="test.record").exists()

    def test_audit_records_cannot_be_bulk_updated(self):
        AuditLog.objects.create(
            tenant_id=self.tenant.id,
            actor_id=None,
            action="test.record",
        )
        with self.assertRaises(TypeError):
            AuditLog.objects.filter(action="test.record").update(
                action="test.overwritten"
            )


class IsolationAndSanitizationTests(BaseAuditSetup):
    def test_cross_tenant_audit_records_isolated(self):
        other = Tenant.objects.create(name="Other Corp")
        AuditService.record(
            action="test.tenant_a",
            tenant_id=self.tenant.id,
            after={"value": "a"},
        )
        AuditService.record(
            action="test.tenant_b",
            tenant_id=other.id,
            after={"value": "b"},
        )
        assert (
            AuditLog.objects.for_tenant(self.tenant.id)
            .filter(action="test.tenant_a")
            .exists()
        )
        assert not (
            AuditLog.objects.for_tenant(self.tenant.id)
            .filter(action="test.tenant_b")
            .exists()
        )
        assert (
            AuditLog.objects.for_tenant(other.id)
            .filter(action="test.tenant_b")
            .exists()
        )

    def test_sensitive_keys_never_persisted(self):
        AuditService.record(
            action="test.secrets",
            tenant_id=self.tenant.id,
            after={
                "email": "user@example.com",
                "password": "SuperSecret",
                "refresh_token": "abc123",
                "api_key": "k-123",
            },
        )
        record = AuditLog.objects.get(action="test.secrets")
        assert "password" not in record.after_data
        assert "refresh_token" not in record.after_data
        assert "api_key" not in record.after_data
        assert record.after_data["email"] == "user@example.com"
        assert len(record.after_data) == 1

    def test_no_audit_record_on_failed_operation(self):
        other = Tenant.objects.create(name="Other Corp")
        other_product = Product.objects.create(
            tenant=other, sku="OTHR", name="Other", unit="pcs"
        )
        resp = self.client.post(
            reverse("adjustment-list"),
            {
                "number": "ADJ-X1",
                "adjustment_date": "2026-09-05",
                "reason": "Should fail",
                "lines": [
                    {"product_id": str(other_product.id), "quantity": "5"}
                ],
            },
            format="json",
            **self.h,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert StockAdjustment.objects.count() == 0
        assert (
            AuditLog.objects.filter(action="inventory.adjustment.create").count()
            == 0
        )