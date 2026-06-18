import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.core.models import Tenant
from apps.accounts.models import User, Membership
from apps.accounting.models import Account


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


class AccountCreationTests(BaseSetup):

    def test_create_root_asset_account(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset", "description": "Cash on hand"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Cash")
        self.assertEqual(resp.data["type"], "Asset")
        self.assertTrue(resp.data["is_active"])
        self.assertIsNone(resp.data["parent_id"])
        self.assertIn("id", resp.data)

    def test_create_account_all_types(self):
        h = self.admin_h()
        for t in ["Asset", "Liability", "Equity", "Revenue", "Expense"]:
            resp = self.client.post(
                reverse("account-list"),
                {"name": f"Test {t}", "type": t},
                format="json",
                **h,
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            self.assertEqual(resp.data["type"], t)

    def test_create_child_account(self):
        h = self.admin_h()
        parent = self.client.post(
            reverse("account-list"),
            {"name": "Current Assets", "type": "Asset"},
            format="json",
            **h,
        ).data
        child = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset", "parent_id": parent["id"]},
            format="json",
            **h,
        ).data
        self.assertEqual(child["parent_id"], parent["id"])

    def test_create_account_without_name_returns_400(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("account-list"),
            {"type": "Asset"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_account_without_type_returns_400(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("account-list"),
            {"name": "NoType"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_accounts(self):
        h = self.admin_h()
        self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        )
        resp = self.client.get(reverse("account-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Cash")

    def test_list_accounts_filter_by_type(self):
        h = self.admin_h()
        self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        )
        self.client.post(
            reverse("account-list"),
            {"name": "Revenue", "type": "Revenue"},
            format="json",
            **h,
        )
        resp = self.client.get(
            reverse("account-list") + "?type=Asset", **h
        )
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["type"], "Asset")

    def test_list_accounts_tree(self):
        h = self.admin_h()
        p = self.client.post(
            reverse("account-list"),
            {"name": "Assets", "type": "Asset"},
            format="json",
            **h,
        ).data
        self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset", "parent_id": p["id"]},
            format="json",
            **h,
        )
        resp = self.client.get(
            reverse("account-list") + "?tree=true", **h
        )
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Assets")
        self.assertEqual(len(resp.data[0]["children"]), 1)

    def test_deactivate_account(self):
        h = self.admin_h()
        acct = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        resp = self.client.patch(
            reverse("account-detail", args=[acct["id"]]),
            {"is_active": False},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_active"])

    def test_cannot_deactivate_account_with_children(self):
        h = self.admin_h()
        p = self.client.post(
            reverse("account-list"),
            {"name": "Assets", "type": "Asset"},
            format="json",
            **h,
        ).data
        self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset", "parent_id": p["id"]},
            format="json",
            **h,
        )
        resp = self.client.patch(
            reverse("account-detail", args=[p["id"]]),
            {"is_active": False},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        acct_data = self.client.get(
            reverse("account-detail", args=[p["id"]]), **h
        ).data
        self.assertTrue(acct_data["is_active"])

    def test_update_account_name(self):
        h = self.admin_h()
        acct = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        resp = self.client.patch(
            reverse("account-detail", args=[acct["id"]]),
            {"name": "Petty Cash"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Petty Cash")

    def test_update_account_type_fails_if_used(self):
        h = self.admin_h()
        cash = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        rev = self.client.post(
            reverse("account-list"),
            {"name": "Revenue", "type": "Revenue"},
            format="json",
            **h,
        ).data
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Test",
                "reference": "JE-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.patch(
            reverse("account-detail", args=[cash["id"]]),
            {"type": "Liability"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated = self.client.get(
            reverse("account-detail", args=[cash["id"]]), **h
        ).data
        self.assertEqual(updated["type"], "Asset")


class AccountPermissionsTests(BaseSetup):

    def test_no_auth_returns_401(self):
        resp = self.client.get(reverse("account-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manager_cannot_list_accounts(self):
        h = self.manager_h()
        resp = self.client.get(reverse("account-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_accountant_can_list_accounts(self):
        h = self.accountant_h()
        resp = self.client.get(reverse("account-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_accountant_can_create_account(self):
        h = self.accountant_h()
        resp = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class JournalEntryCreationTests(BaseSetup):

    def _make_accounts(self, h):
        cash = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        rev = self.client.post(
            reverse("account-list"),
            {"name": "Sales Revenue", "type": "Revenue"},
            format="json",
            **h,
        ).data
        return cash, rev

    def test_create_balanced_journal_entry(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale for cash",
                "reference": "JE-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "1000.00"},
                    {"account_id": rev["id"], "credit": "1000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["reference"], "JE-001")
        self.assertEqual(float(resp.data["total_debit"]), 1000.00)
        self.assertEqual(float(resp.data["total_credit"]), 1000.00)

    def test_imbalanced_entry_returns_400(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Imbalanced",
                "reference": "JE-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "99.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_single_line_entry_returns_400(self):
        h = self.admin_h()
        cash, _ = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Single line",
                "reference": "JE-003",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_entry_returns_400(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Zero amounts",
                "reference": "JE-004",
                "lines": [
                    {"account_id": cash["id"], "debit": "0.00"},
                    {"account_id": rev["id"], "credit": "0.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_line_with_both_debit_and_credit_returns_400(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Both sides",
                "reference": "JE-005",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00", "credit": "50.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_journal_entry(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        je = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-006",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        ).data
        resp = self.client.post(
            reverse("journalentry-post", args=[je["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["posted"])
        self.assertIsNotNone(resp.data["posted_at"])

    def test_cannot_post_twice(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        je = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-007",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        ).data
        self.client.post(reverse("journalentry-post", args=[je["id"]]), **h)
        resp = self.client.post(
            reverse("journalentry-post", args=[je["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_journal_entries(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-008",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(reverse("journalentry-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_entries_filtered_by_date(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Jan entry",
                "reference": "JE-009",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-02-15",
                "description": "Feb entry",
                "reference": "JE-010",
                "lines": [
                    {"account_id": cash["id"], "debit": "200.00"},
                    {"account_id": rev["id"], "credit": "200.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(
            reverse("journalentry-list") + "?date_from=2026-02-01&date_to=2026-02-28",
            **h,
        )
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["reference"], "JE-010")

    def test_journal_entry_immutable_no_update(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        je = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Test",
                "reference": "JE-IMM",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        ).data
        resp = self.client.put(
            reverse("journalentry-detail", args=[je["id"]]),
            {"description": "Changed"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        resp2 = self.client.patch(
            reverse("journalentry-detail", args=[je["id"]]),
            {"description": "Changed"},
            format="json",
            **h,
        )
        self.assertEqual(resp2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_journal_entry_immutable_no_delete(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        je = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Test",
                "reference": "JE-DEL",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        ).data
        resp = self.client.delete(
            reverse("journalentry-detail", args=[je["id"]]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_duplicate_reference_per_tenant_returns_400(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "First",
                "reference": "JE-DUP",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-16",
                "description": "Duplicate ref",
                "reference": "JE-DUP",
                "lines": [
                    {"account_id": cash["id"], "debit": "200.00"},
                    {"account_id": rev["id"], "credit": "200.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LedgerAndBalanceTests(BaseSetup):

    def _seed_data(self, h):
        cash = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        rev = self.client.post(
            reverse("account-list"),
            {"name": "Sales Revenue", "type": "Revenue"},
            format="json",
            **h,
        ).data
        exp = self.client.post(
            reverse("account-list"),
            {"name": "Rent Expense", "type": "Expense"},
            format="json",
            **h,
        ).data
        eq = self.client.post(
            reverse("account-list"),
            {"name": "Common Stock", "type": "Equity"},
            format="json",
            **h,
        ).data
        liab = self.client.post(
            reverse("account-list"),
            {"name": "Loan Payable", "type": "Liability"},
            format="json",
            **h,
        ).data
        return cash, rev, exp, eq, liab

    def test_ledger_running_balance(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)

        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-01",
                "description": "Initial investment",
                "reference": "JE-BAL-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "10000.00"},
                    {"account_id": eq["id"], "credit": "10000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-BAL-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-20",
                "description": "Rent payment",
                "reference": "JE-BAL-003",
                "lines": [
                    {"account_id": exp["id"], "debit": "2000.00"},
                    {"account_id": cash["id"], "credit": "2000.00"},
                ],
            },
            format="json",
            **h,
        )

        ledger = self.client.get(
            reverse("ledger-list") + f"?account_id={cash['id']}", **h
        ).data
        self.assertEqual(ledger["account"]["name"], "Cash")
        entries = ledger["entries"]
        self.assertEqual(len(entries), 3)
        self.assertEqual(float(entries[0]["running_balance"]), 10000.00)
        self.assertEqual(float(entries[1]["running_balance"]), 10500.00)
        self.assertEqual(float(entries[2]["running_balance"]), 8500.00)
        self.assertEqual(float(ledger["totals"]["closing_balance"]), 8500.00)

    def test_ledger_date_filter(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-01",
                "description": "Investment",
                "reference": "JE-DT-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "10000.00"},
                    {"account_id": eq["id"], "credit": "10000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-02-01",
                "description": "Sale",
                "reference": "JE-DT-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        )
        ledger = self.client.get(
            reverse("ledger-list")
            + f"?account_id={cash['id']}&date_from=2026-02-01&date_to=2026-02-28",
            **h,
        ).data
        self.assertEqual(len(ledger["entries"]), 1)

    def test_ledger_missing_account_id_returns_400(self):
        h = self.admin_h()
        resp = self.client.get(reverse("ledger-list"), **h)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trial_balance(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-01",
                "description": "Investment",
                "reference": "JE-TB-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "10000.00"},
                    {"account_id": eq["id"], "credit": "10000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-TB-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(reverse("report-trial-balance"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["report_type"], "trial-balance")
        totals = resp.data["totals"]
        self.assertEqual(float(totals["total_debit"]), float(totals["total_credit"]))

    def test_trial_balance_date_filter(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-01",
                "description": "Investment",
                "reference": "JE-TBD-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "10000.00"},
                    {"account_id": eq["id"], "credit": "10000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-02-01",
                "description": "Sale",
                "reference": "JE-TBD-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "500.00"},
                    {"account_id": rev["id"], "credit": "500.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(
            reverse("report-trial-balance")
            + "?date_from=2026-02-01&date_to=2026-02-28",
            **h,
        )
        totals = resp.data["totals"]
        self.assertEqual(float(totals["total_debit"]), 500.00)

    def test_income_statement(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-IS-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "5000.00"},
                    {"account_id": rev["id"], "credit": "5000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-20",
                "description": "Rent",
                "reference": "JE-IS-002",
                "lines": [
                    {"account_id": exp["id"], "debit": "2000.00"},
                    {"account_id": cash["id"], "credit": "2000.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(reverse("report-income-statement"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["report_type"], "income-statement")
        self.assertEqual(float(resp.data["total_revenue"]), 5000.00)
        self.assertEqual(float(resp.data["total_expenses"]), 2000.00)
        self.assertEqual(float(resp.data["net_income"]), 3000.00)

    def test_balance_sheet(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._seed_data(h)
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-01",
                "description": "Initial investment",
                "reference": "JE-BS-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "50000.00"},
                    {"account_id": eq["id"], "credit": "50000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-10",
                "description": "Loan",
                "reference": "JE-BS-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "20000.00"},
                    {"account_id": liab["id"], "credit": "20000.00"},
                ],
            },
            format="json",
            **h,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Sale",
                "reference": "JE-BS-003",
                "lines": [
                    {"account_id": cash["id"], "debit": "5000.00"},
                    {"account_id": rev["id"], "credit": "5000.00"},
                ],
            },
            format="json",
            **h,
        )
        resp = self.client.get(reverse("report-balance-sheet"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["report_type"], "balance-sheet")
        self.assertEqual(float(resp.data["total_assets"]), 75000.00)
        self.assertEqual(float(resp.data["total_liabilities"]), 20000.00)
        self.assertEqual(float(resp.data["total_equity"]), 55000.00)
        self.assertEqual(
            float(resp.data["total_liabilities_and_equity"]), 75000.00
        )


class ReportPermissionsTests(BaseSetup):

    def test_manager_can_view_reports(self):
        h = self.manager_h()
        resp = self.client.get(reverse("report-trial-balance"), **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_cannot_create_account(self):
        h = self.manager_h()
        resp = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MultiTenantIsolationTests(APITestCase):

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A")
        self.tenant_b = Tenant.objects.create(name="Tenant B")
        for t, suffix in [(self.tenant_a, "a"), (self.tenant_b, "b")]:
            admin = User.objects.create_user(
                email=f"admin@{suffix}.com", password="SecurePass123"
            )
            Membership.objects.create(
                user=admin, tenant=t, role=Membership.Role.ADMIN
            )

    def test_accounts_isolated_between_tenants(self):
        h_a = _headers(self.client, email="admin@a.com", tenant=self.tenant_a.id)
        h_b = _headers(self.client, email="admin@b.com", tenant=self.tenant_b.id)

        self.client.post(
            reverse("account-list"),
            {"name": "TenantA-Cash", "type": "Asset"},
            format="json",
            **h_a,
        )
        self.client.post(
            reverse("account-list"),
            {"name": "TenantB-Cash", "type": "Asset"},
            format="json",
            **h_b,
        )

        list_a = self.client.get(reverse("account-list"), **h_a).data
        list_b = self.client.get(reverse("account-list"), **h_b).data
        self.assertEqual(len(list_a), 1)
        self.assertEqual(len(list_b), 1)
        self.assertEqual(list_a[0]["name"], "TenantA-Cash")
        self.assertEqual(list_b[0]["name"], "TenantB-Cash")

    def test_journal_entries_isolated_between_tenants(self):
        h_a = _headers(self.client, email="admin@a.com", tenant=self.tenant_a.id)
        h_b = _headers(self.client, email="admin@b.com", tenant=self.tenant_b.id)

        acct_a = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h_a,
        ).data
        rev_a = self.client.post(
            reverse("account-list"),
            {"name": "Revenue", "type": "Revenue"},
            format="json",
            **h_a,
        ).data
        acct_b = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h_b,
        ).data
        rev_b = self.client.post(
            reverse("account-list"),
            {"name": "Revenue", "type": "Revenue"},
            format="json",
            **h_b,
        ).data

        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Tenant A sale",
                "reference": "JE-A-001",
                "lines": [
                    {"account_id": acct_a["id"], "debit": "100.00"},
                    {"account_id": rev_a["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h_a,
        )
        self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Tenant B sale",
                "reference": "JE-B-001",
                "lines": [
                    {"account_id": acct_b["id"], "debit": "200.00"},
                    {"account_id": rev_b["id"], "credit": "200.00"},
                ],
            },
            format="json",
            **h_b,
        )

        list_a = self.client.get(reverse("journalentry-list"), **h_a).data
        list_b = self.client.get(reverse("journalentry-list"), **h_b).data
        self.assertEqual(len(list_a), 1)
        self.assertEqual(len(list_b), 1)
        self.assertEqual(list_a[0]["reference"], "JE-A-001")
        self.assertEqual(list_b[0]["reference"], "JE-B-001")

    def test_cross_tenant_account_not_accessible(self):
        h_a = _headers(self.client, email="admin@a.com", tenant=self.tenant_a.id)
        h_b = _headers(self.client, email="admin@b.com", tenant=self.tenant_b.id)

        acct_a = self.client.post(
            reverse("account-list"),
            {"name": "Secret-A", "type": "Asset"},
            format="json",
            **h_a,
        ).data

        resp = self.client.get(
            reverse("account-detail", args=[acct_a["id"]]), **h_b
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class APIErrorHandlingTests(BaseSetup):

    def test_missing_tenant_header_returns_200(self):
        resp = self.client.post(
            reverse("auth-login"),
            {"email": "admin@example.com", "password": "SecurePass123"},
            format="json",
        )
        token = resp.data["access"]
        resp2 = self.client.get(
            reverse("account-list"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)

    def test_account_not_found_returns_404(self):
        h = self.admin_h()
        resp = self.client.get(
            reverse("account-detail", args=["00000000-0000-0000-0000-000000000999"]),
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_ledger_account_not_found_returns_404(self):
        h = self.admin_h()
        resp = self.client.get(
            reverse("ledger-list")
            + "?account_id=00000000-0000-0000-0000-000000000999",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_nonexistent_entry_returns_404(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("journalentry-post", args=["00000000-0000-0000-0000-000000000999"]),
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_entry_with_nonexistent_account_returns_400(self):
        h = self.admin_h()
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Bad account",
                "reference": "JE-ERR-001",
                "lines": [
                    {
                        "account_id": "00000000-0000-0000-0000-000000000999",
                        "debit": "100.00",
                    },
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_amounts_returns_400(self):
        h = self.admin_h()
        cash = self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h,
        ).data
        rev = self.client.post(
            reverse("account-list"),
            {"name": "Revenue", "type": "Revenue"},
            format="json",
            **h,
        ).data
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Negative",
                "reference": "JE-NEG",
                "lines": [
                    {"account_id": cash["id"], "debit": "-100.00"},
                    {"account_id": rev["id"], "credit": "100.00"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
