from django.urls import reverse
from rest_framework import status

from apps.accounting.tests.test_accounting_api import BaseSetup


class JournalEntryListPaginationTests(BaseSetup):
    def test_journal_entry_list_is_paginated_envelope(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        for i in range(3):
            self.client.post(
                reverse("journalentry-list"),
                {
                    "date": "2026-01-15",
                    "description": f"Entry {i}",
                    "reference": f"JE-PAG-00{i}",
                    "lines": [
                        {"account_id": cash["id"], "debit": "100.00"},
                        {"account_id": rev["id"], "credit": "100.00"},
                    ],
                },
                format="json",
                **h,
            )
        resp = self.client.get(
            reverse("journalentry-list") + "?page_size=2", **h
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])

    def _make_accounts(self, h):
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
        return cash, rev