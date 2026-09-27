from decimal import Decimal

from rest_framework import status
from django.urls import reverse

from apps.accounting.models import Account
from apps.accounting.services import JournalEntryService
from apps.accounting.tests.test_accounting_api import BaseSetup, _headers
from apps.core.models import Tenant
from apps.accounts.models import User, Membership


class FinancialIntegritySetup(BaseSetup):
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

    def _create_draft(self, h, payload):
        resp = self.client.post(
            reverse("journalentry-list"), payload, format="json", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data

    def _post(self, h, entry_id):
        resp = self.client.post(
            reverse("journalentry-post", args=[entry_id]), **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data


class PostedEntryReportTests(FinancialIntegritySetup):
    """AUD-001: drafts must never flow into ledger/reports; posting must be explicit."""

    def _sale_payload(self, reference, amount="1000.00", date="2026-01-15"):
        return {
            "date": date,
            "description": "Sale",
            "reference": reference,
            "lines": [
                {"account_id": self.cash["id"], "debit": amount},
                {"account_id": self.rev["id"], "credit": amount},
            ],
        }

    def setUp(self):
        super().setUp()
        h = self.admin_h()
        self.cash, self.rev, self.exp, self.eq, self.liab = self._make_accounts(h)
        self.h = h

    def test_draft_excluded_from_ledger(self):
        draft = self._create_draft(self.h, self._sale_payload("JE-DL-001"))
        self.assertFalse(draft["posted"])
        ledger = self.client.get(
            reverse("ledger-list") + f"?account_id={self.cash['id']}", **self.h
        ).data
        self.assertEqual(ledger["entries"], [])
        self.assertEqual(ledger["totals"]["total_debit"], "0.0000")
        self.assertEqual(ledger["totals"]["total_credit"], "0.0000")
        self.assertEqual(ledger["totals"]["closing_balance"], "0.0000")

    def test_draft_excluded_from_trial_balance(self):
        self._create_draft(self.h, self._sale_payload("JE-DTB-001"))
        resp = self.client.get(reverse("report-trial-balance"), **self.h).data
        self.assertEqual(resp["rows"], [])
        self.assertEqual(resp["totals"]["total_debit"], "0.0000")
        self.assertEqual(resp["totals"]["total_credit"], "0.0000")

    def test_draft_excluded_from_income_statement(self):
        self._create_draft(self.h, self._sale_payload("JE-DIS-001"))
        resp = self.client.get(reverse("report-income-statement"), **self.h).data
        self.assertEqual(resp["revenues"], [])
        self.assertEqual(resp["expenses"], [])
        self.assertEqual(resp["total_revenue"], "0.0000")
        self.assertEqual(resp["total_expenses"], "0.0000")
        self.assertEqual(resp["net_income"], "0.0000")

    def test_draft_excluded_from_balance_sheet(self):
        self._create_draft(
            self.h,
            {
                "date": "2026-01-15",
                "description": "Holding",
                "reference": "JE-DBS-001",
                "lines": [
                    {"account_id": self.cash["id"], "debit": "10000.00"},
                    {"account_id": self.eq["id"], "credit": "10000.00"},
                ],
            },
        )
        resp = self.client.get(reverse("report-balance-sheet"), **self.h).data
        self.assertEqual(resp["assets"], [])
        self.assertEqual(resp["equity"], [])
        self.assertEqual(resp["total_assets"], "0.0000")
        self.assertEqual(resp["total_liabilities_and_equity"], "0.0000")

    def test_draft_cannot_affect_financial_totals(self):
        self._create_draft(self.h, self._sale_payload("JE-TOT-001", amount="999999.00"))
        self._create_draft(
            self.h,
            {
                "date": "2026-01-16",
                "description": "Expense draft",
                "reference": "JE-TOT-002",
                "lines": [
                    {"account_id": self.exp["id"], "debit": "888888.00"},
                    {"account_id": self.cash["id"], "credit": "888888.00"},
                ],
            },
        )
        tb = self.client.get(reverse("report-trial-balance"), **self.h).data
        self.assertEqual(tb["totals"]["total_debit"], "0.0000")
        self.assertEqual(tb["totals"]["total_credit"], "0.0000")
        isr = self.client.get(reverse("report-income-statement"), **self.h).data
        self.assertEqual(isr["total_revenue"], "0.0000")
        self.assertEqual(isr["total_expenses"], "0.0000")

    def test_posted_entry_appears_in_all_reports(self):
        draft = self._create_draft(self.h, self._sale_payload("JE-PA-001", amount="500.00"))
        self.assertFalse(draft["posted"])

        posted = self._post(self.h, draft["id"])
        self.assertTrue(posted["posted"])
        self.assertIsNotNone(posted["posted_at"])

        ledger = self.client.get(
            reverse("ledger-list") + f"?account_id={self.cash['id']}", **self.h
        ).data
        self.assertEqual(len(ledger["entries"]), 1)
        self.assertEqual(ledger["entries"][0]["reference"], "JE-PA-001")
        self.assertEqual(ledger["entries"][0]["running_balance"], "500.0000")
        self.assertEqual(ledger["totals"]["closing_balance"], "500.0000")

        tb = self.client.get(reverse("report-trial-balance"), **self.h).data
        self.assertEqual(tb["totals"]["total_debit"], "500.0000")
        self.assertEqual(tb["totals"]["total_credit"], "500.0000")

        isr = self.client.get(reverse("report-income-statement"), **self.h).data
        self.assertEqual(isr["total_revenue"], "500.0000")
        self.assertEqual(isr["net_income"], "500.0000")

        bs = self.client.get(reverse("report-balance-sheet"), **self.h).data
        self.assertEqual(bs["total_assets"], "500.0000")
        self.assertEqual(bs["total_equity"], "500.0000")
        self.assertEqual(bs["total_liabilities_and_equity"], "500.0000")

    def test_explicit_post_moves_draft_into_reports(self):
        draft = self._create_draft(self.h, self._sale_payload("JE-EP-001"))
        before = self.client.get(reverse("report-trial-balance"), **self.h).data
        self.assertEqual(before["totals"]["total_debit"], "0.0000")

        self._post(self.h, draft["id"])

        after = self.client.get(reverse("report-trial-balance"), **self.h).data
        self.assertEqual(after["totals"]["total_debit"], "1000.0000")
        self.assertEqual(after["totals"]["total_credit"], "1000.0000")

    def test_journal_list_exposes_posted_flag(self):
        self._create_draft(self.h, self._sale_payload("JE-FLAG-001"))
        resp = self.client.get(reverse("journalentry-list"), **self.h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertIn("posted", resp.data["results"][0])
        self.assertFalse(resp.data["results"][0]["posted"])


class BalanceSheetNetLossTests(FinancialIntegritySetup):
    """AUD-002: balance sheet must balance in loss, profit, and zero-income periods."""

    def _scenario(self, net_income):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)

        def post_entry(reference, lines):
            entry = self._create_draft(h, {
                "date": "2026-01-01",
                "description": reference,
                "reference": reference,
                "lines": lines,
            })
            self._post(h, entry["id"])

        post_entry("JE-BSINV-001", [
            {"account_id": cash["id"], "debit": "10000.00"},
            {"account_id": eq["id"], "credit": "10000.00"},
        ])
        post_entry("JE-BSREV-001", [
            {"account_id": cash["id"], "debit": "5000.00"},
            {"account_id": rev["id"], "credit": "5000.00"},
        ])
        post_entry("JE-BSEXP-001", [
            {"account_id": exp["id"], "debit": f"{5000.00 - net_income:.4f}"},
            {"account_id": cash["id"], "credit": f"{5000.00 - net_income:.4f}"},
        ])
        resp = self.client.get(reverse("report-balance-sheet"), **h).data
        return resp

    def test_net_loss_balance_sheet_balances(self):
        resp = self._scenario(net_income=-3000.00)
        self.assertEqual(Decimal(resp["total_assets"]), Decimal("7000.0000"))
        self.assertEqual(Decimal(resp["total_liabilities"]), Decimal("0.0000"))
        self.assertEqual(Decimal(resp["total_equity"]), Decimal("7000.0000"))
        retained = [r for r in resp["equity"] if r["account_id"] == "retained-earnings"]
        self.assertEqual(len(retained), 1)
        self.assertEqual(Decimal(retained[0]["balance"]), Decimal("-3000.0000"))
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities"]) + Decimal(resp["total_equity"]),
        )
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities_and_equity"]),
        )

    def test_positive_net_income_balance_sheet_balances(self):
        resp = self._scenario(net_income=3000.00)
        self.assertEqual(Decimal(resp["total_assets"]), Decimal("13000.0000"))
        self.assertEqual(Decimal(resp["total_equity"]), Decimal("13000.0000"))
        retained = [r for r in resp["equity"] if r["account_id"] == "retained-earnings"]
        self.assertEqual(Decimal(retained[0]["balance"]), Decimal("3000.0000"))
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities_and_equity"]),
        )

    def test_zero_net_income_balance_sheet_balances(self):
        resp = self._scenario(net_income=0.00)
        self.assertEqual(Decimal(resp["total_assets"]), Decimal("10000.0000"))
        self.assertEqual(Decimal(resp["total_equity"]), Decimal("10000.0000"))
        retained = [r for r in resp["equity"] if r["account_id"] == "retained-earnings"]
        self.assertEqual(retained, [])
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities_and_equity"]),
        )

    def test_negative_asset_balance_not_hidden(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)

        def post_entry(reference, lines):
            entry = self._create_draft(h, {
                "date": "2026-01-01",
                "description": reference,
                "reference": reference,
                "lines": lines,
            })
            self._post(h, entry["id"])

        post_entry("JE-LOSS-001", [
            {"account_id": cash["id"], "debit": "5000.00"},
            {"account_id": eq["id"], "credit": "5000.00"},
        ])
        post_entry("JE-LOSS-002", [
            {"account_id": exp["id"], "debit": "8000.00"},
            {"account_id": cash["id"], "credit": "8000.00"},
        ])
        resp = self.client.get(reverse("report-balance-sheet"), **h).data
        self.assertEqual(Decimal(resp["total_assets"]), Decimal("-3000.0000"))
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities_and_equity"]),
        )
        self.assertEqual(
            Decimal(resp["total_assets"]),
            Decimal(resp["total_liabilities"]) + Decimal(resp["total_equity"]),
        )


class DecimalPrecisionTests(FinancialIntegritySetup):
    """AUD-005: accounting math must be exact Decimal, not float."""

    def test_serializer_rejects_imbalance_of_one_thousandth(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Tiny imbalance",
                "reference": "JE-DEC-API-001",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.0000"},
                    {"account_id": rev["id"], "credit": "100.0010"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_serializer_accepts_exact_fractional_balance(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-15",
                "description": "Exact fractional",
                "reference": "JE-DEC-API-002",
                "lines": [
                    {"account_id": cash["id"], "debit": "100.0001"},
                    {"account_id": rev["id"], "credit": "100.0001"},
                ],
            },
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Decimal(str(resp.data["total_debit"])), Decimal("100.0001")
        )
        self.assertEqual(
            Decimal(str(resp.data["total_credit"])), Decimal("100.0001")
        )

    def test_post_entry_rejects_tiny_imbalance(self):
        cash = Account.objects.create(
            tenant_id=self.tenant.id, name="Cash", type=Account.Type.ASSET
        )
        rev = Account.objects.create(
            tenant_id=self.tenant.id, name="Rev", type=Account.Type.REVENUE
        )
        entry = JournalEntryService(self.tenant.id).create_entry(
            date="2026-01-15",
            description="Tiny imbalance",
            reference="JE-DEC-SVC-001",
            lines_data=[
                {"account_id": cash.pk, "debit": Decimal("100.0010")},
                {"account_id": rev.pk, "credit": Decimal("100.0000")},
            ],
        )
        with self.assertRaises(ValueError):
            JournalEntryService(self.tenant.id).post_entry(entry.pk)
        entry.refresh_from_db()
        self.assertFalse(entry.posted)

    def test_ledger_running_balance_exact_decimal(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)

        def post_entry(reference, lines):
            entry = self._create_draft(h, {
                "date": "2026-01-01",
                "description": reference,
                "reference": reference,
                "lines": lines,
            })
            self._post(h, entry["id"])

        post_entry("JE-DEC-LED-001", [
            {"account_id": cash["id"], "debit": "0.0001"},
            {"account_id": eq["id"], "credit": "0.0001"},
        ])
        post_entry("JE-DEC-LED-002", [
            {"account_id": cash["id"], "debit": "0.0002"},
            {"account_id": rev["id"], "credit": "0.0002"},
        ])
        post_entry("JE-DEC-LED-003", [
            {"account_id": exp["id"], "debit": "0.0003"},
            {"account_id": cash["id"], "credit": "0.0003"},
        ])

        ledger = self.client.get(
            reverse("ledger-list") + f"?account_id={cash['id']}", **h
        ).data
        running = [Decimal(e["running_balance"]) for e in ledger["entries"]]
        self.assertEqual(
            running, [Decimal("0.0001"), Decimal("0.0003"), Decimal("0.0000")]
        )
        self.assertEqual(
            Decimal(ledger["totals"]["closing_balance"]), Decimal("0.0000")
        )

    def test_trial_balance_totals_exact(self):
        h = self.admin_h()
        cash, rev, exp, eq, liab = self._make_accounts(h)

        def post_entry(reference, amount):
            entry = self._create_draft(h, {
                "date": "2026-01-01",
                "description": reference,
                "reference": reference,
                "lines": [
                    {"account_id": cash["id"], "debit": amount},
                    {"account_id": rev["id"], "credit": amount},
                ],
            })
            self._post(h, entry["id"])

        post_entry("JE-DEC-TB-001", "55.25")
        post_entry("JE-DEC-TB-002", "44.75")
        resp = self.client.get(reverse("report-trial-balance"), **h).data
        self.assertEqual(resp["totals"]["total_debit"], "100.0000")
        self.assertEqual(resp["totals"]["total_credit"], "100.0000")


class NetLossBalanceSheetIsolationTests(FinancialIntegritySetup):
    def test_loss_balance_sheet_tenant_isolated(self):
        h = self.admin_h()
        tenant_b = Tenant.objects.create(name="Other Corp")
        admin_b = User.objects.create_user(
            email="adminb@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=admin_b, tenant=tenant_b, role=Membership.Role.ADMIN
        )
        h_b = _headers(self.client, email="adminb@example.com", tenant=tenant_b.id)

        assets_a, rev_a, exp_a, eq_a, liab_a = self._make_accounts(h)
        self.client.post(
            reverse("account-list"),
            {"name": "Cash", "type": "Asset"},
            format="json",
            **h_b,
        )
        self.client.post(
            reverse("account-list"),
            {"name": "Equity", "type": "Equity"},
            format="json",
            **h_b,
        )

        def post_a(reference, lines):
            entry = self._create_draft(h, {
                "date": "2026-01-01",
                "description": reference,
                "reference": reference,
                "lines": lines,
            })
            self._post(h, entry["id"])

        post_a("JE-ISO-L-001", [
            {"account_id": assets_a["id"], "debit": "5000.00"},
            {"account_id": eq_a["id"], "credit": "5000.00"},
        ])
        post_a("JE-ISO-L-002", [
            {"account_id": exp_a["id"], "debit": "7000.00"},
            {"account_id": assets_a["id"], "credit": "7000.00"},
        ])

        resp_a = self.client.get(reverse("report-balance-sheet"), **h).data
        self.assertEqual(Decimal(resp_a["total_assets"]), Decimal("-2000.0000"))
        self.assertEqual(
            Decimal(resp_a["total_assets"]),
            Decimal(resp_a["total_liabilities_and_equity"]),
        )

        resp_b = self.client.get(reverse("report-balance-sheet"), **h_b).data
        self.assertEqual(resp_b["assets"], [])
        self.assertEqual(resp_b["equity"], [])
        self.assertEqual(resp_b["total_assets"], "0.0000")
        self.assertEqual(resp_b["total_liabilities_and_equity"], "0.0000")