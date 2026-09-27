"""AUD-030: balance invariants are Decimal-exact, not tolerance-based.

The previous implementation treated any imbalance below 0.01 as balanced, so a
real out-of-balance journal entry could pass validation. These tests pin the
exact-equality behaviour at the model, service, and API layers.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.accounting.services import JournalEntryService
from apps.accounting.tests.test_accounting_api import BaseSetup
from apps.core.models import Tenant


class DecimalExactBalanceTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Corp")
        self.debit_account = Account.objects.create(
            tenant=self.tenant, name="Cash", type=Account.Type.ASSET
        )
        self.credit_account = Account.objects.create(
            tenant=self.tenant, name="Revenue", type=Account.Type.REVENUE
        )

    def _entry(self, reference="JE-1"):
        return JournalEntry.objects.create(
            tenant=self.tenant,
            date="2026-01-05",
            description="entry",
            reference=reference,
        )

    def _lines(self, entry, debit, credit):
        JournalEntryLine.objects.create(
            entry=entry, account=self.debit_account, debit=Decimal(debit)
        )
        JournalEntryLine.objects.create(
            entry=entry, account=self.credit_account, credit=Decimal(credit)
        )
        return entry

    def test_exact_match_is_balanced(self):
        entry = self._lines(self._entry(), "100.0000", "100.0000")
        self.assertTrue(entry.is_balanced)

    def test_one_cent_imbalance_is_not_balanced(self):
        entry = self._lines(self._entry(), "100.0000", "99.9900")
        self.assertFalse(entry.is_balanced)

    def test_fractional_cent_imbalance_is_not_balanced(self):
        # 0.005 was inside the old "< 0.01" tolerance and wrongly passed.
        entry = self._lines(self._entry(), "100.0000", "99.9950")
        self.assertFalse(entry.is_balanced)

    def test_minimum_precision_imbalance_is_not_balanced(self):
        entry = self._lines(self._entry(), "100.0000", "99.9999")
        self.assertFalse(entry.is_balanced)

    def test_totals_are_decimal(self):
        entry = self._lines(self._entry(), "100.0000", "100.0000")
        self.assertIsInstance(entry.total_debit, Decimal)
        self.assertIsInstance(entry.total_credit, Decimal)

    def test_entry_without_lines_is_balanced_but_not_postable(self):
        entry = self._entry()
        self.assertTrue(entry.is_balanced)
        service = JournalEntryService(self.tenant.id)
        with self.assertRaises(ValueError):
            service.post_entry(entry.id)

    def test_clean_rejects_small_imbalance(self):
        entry = self._lines(self._entry(), "100.0000", "99.9950")
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_post_entry_rejects_small_imbalance(self):
        entry = self._lines(self._entry(), "100.0000", "99.9950")
        service = JournalEntryService(self.tenant.id)
        with self.assertRaises(ValueError):
            service.post_entry(entry.id)
        entry.refresh_from_db()
        self.assertFalse(entry.posted)


class DecimalExactBalanceApiTests(BaseSetup):
    def setUp(self):
        super().setUp()
        self.debit_account = Account.objects.create(
            tenant=self.tenant, name="Cash", type=Account.Type.ASSET
        )
        self.credit_account = Account.objects.create(
            tenant=self.tenant, name="Revenue", type=Account.Type.REVENUE
        )

    def test_api_rejects_small_imbalance(self):
        resp = self.client.post(
            reverse("journalentry-list"),
            {
                "date": "2026-01-05",
                "description": "off by half a cent",
                "lines": [
                    {
                        "account_id": str(self.debit_account.id),
                        "debit": "100.0000",
                        "credit": "0.0000",
                    },
                    {
                        "account_id": str(self.credit_account.id),
                        "debit": "0.0000",
                        "credit": "99.9950",
                    },
                ],
            },
            format="json",
            **self.admin_h(),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertEqual(JournalEntryLine.objects.count(), 0)
