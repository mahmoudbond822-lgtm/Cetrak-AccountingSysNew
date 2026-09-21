from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounting.models import Account, JournalEntry
from apps.accounting.services import JournalEntryService
from apps.accounting.tests.test_accounting_api import BaseSetup
from apps.core.models import Tenant


def _year():
    return timezone.now().year


def _lines():
    return [
        {"debit": "100.00", "credit": "0"},
        {"debit": "0", "credit": "100.00"},
    ]


class AutoJournalEntryReferenceTestCase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Auto Ref Tenant")
        self.service = JournalEntryService(self.tenant.id)
        self.cash = Account.objects.create(
            tenant_id=self.tenant.id, name="Cash", type=Account.Type.ASSET
        )
        self.revenue = Account.objects.create(
            tenant_id=self.tenant.id, name="Revenue", type=Account.Type.REVENUE
        )

    def create_entry(self, reference=None, **overrides):
        kwargs = dict(
            date="2026-09-01",
            description="Opening entry",
            lines_data=[
                {"account_id": self.cash.pk, "debit": "100.00", "credit": "0"},
                {"account_id": self.revenue.pk, "debit": "0", "credit": "100.00"},
            ],
        )
        if reference is not None:
            kwargs["reference"] = reference
        kwargs.update(overrides)
        return self.service.create_entry(**kwargs)

    def test_create_mints_sequential_tenant_unique_references(self):
        one = self.create_entry()
        two = self.create_entry()
        self.assertTrue(one.reference)
        self.assertTrue(two.reference)
        self.assertNotEqual(one.reference, two.reference)
        references = list(
            JournalEntry.objects.filter(tenant_id=self.tenant.id)
            .order_by("reference")
            .values_list("reference", flat=True)
        )
        self.assertEqual(len(references), len(set(references)))

    def test_create_mints_je_year_prefixed_references(self):
        one = self.create_entry()
        self.assertTrue(one.reference.startswith(f"JE-{_year()}-"))
        self.assertEqual(one.reference, f"JE-{_year()}-0001")
        two = self.create_entry()
        self.assertEqual(two.reference, f"JE-{_year()}-0002")

    def test_create_without_reference_arg_mints(self):
        entry = self.service.create_entry(
            date="2026-09-01",
            description="No reference kwarg",
            lines_data=[
                {"account_id": self.cash.pk, "debit": "100.00", "credit": "0"},
                {"account_id": self.revenue.pk, "debit": "0", "credit": "100.00"},
            ],
        )
        self.assertEqual(entry.reference, f"JE-{_year()}-0001")

    def test_create_with_blank_reference_still_mints(self):
        entry = self.create_entry(reference="   ")
        self.assertEqual(entry.reference, f"JE-{_year()}-0001")

    def test_create_with_explicit_reference_preserved(self):
        entry = self.create_entry(reference="JE-2026-0042")
        self.assertEqual(entry.reference, "JE-2026-0042")

    def test_collision_skips_taken_reference(self):
        self.create_entry(reference=f"JE-{_year()}-0001")
        entry = self.create_entry()
        self.assertEqual(entry.reference, f"JE-{_year()}-0002")

    def test_manual_high_reference_then_mint_continues_after_it(self):
        self.create_entry(reference=f"JE-{_year()}-0005")
        entry = self.create_entry()
        self.assertEqual(entry.reference, f"JE-{_year()}-0006")

    def test_non_numeric_legacy_reference_does_not_break_sequence(self):
        JournalEntry.objects.create(
            tenant_id=self.tenant.id,
            date="2026-09-01",
            description="Legacy manual style",
            reference="JE-ABC",
        )
        entry = self.create_entry()
        self.assertEqual(entry.reference, f"JE-{_year()}-0001")

    def test_other_year_reference_ignored_by_current_year_sequence(self):
        other_year = _year() - 1
        JournalEntry.objects.create(
            tenant_id=self.tenant.id,
            date=f"{other_year}-09-01",
            description="Prior year",
            reference=f"JE-{other_year}-0099",
        )
        entry = self.create_entry()
        self.assertEqual(entry.reference, f"JE-{_year()}-0001")

    def test_cross_tenant_references_use_independent_sequences(self):
        other_tenant = Tenant.objects.create(name="Other Tenant")
        other = JournalEntryService(other_tenant.id)
        other_cash = Account.objects.create(
            tenant_id=other_tenant.id, name="Cash", type=Account.Type.ASSET
        )
        other_rev = Account.objects.create(
            tenant_id=other_tenant.id, name="Revenue", type=Account.Type.REVENUE
        )
        mine = self.create_entry()
        theirs = other.create_entry(
            date="2026-09-01",
            description="Other tenant entry",
            lines_data=[
                {"account_id": other_cash.pk, "debit": "100.00", "credit": "0"},
                {"account_id": other_rev.pk, "debit": "0", "credit": "100.00"},
            ],
        )
        self.assertEqual(theirs.reference, mine.reference)
        self.assertEqual(theirs.reference, f"JE-{_year()}-0001")

    def test_next_reference_preview_does_not_consume(self):
        preview = self.service.next_reference()
        self.assertEqual(preview, f"JE-{_year()}-0001")
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertEqual(self.service.next_reference(), preview)

    def test_next_reference_skips_taken(self):
        self.create_entry(reference=f"JE-{_year()}-0001")
        self.assertEqual(
            self.service.next_reference(), f"JE-{_year()}-0002"
        )


class AutoJournalEntryReferenceApiTestCase(BaseSetup):
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

    def _payload(self, cash, rev, **overrides):
        payload = dict(
            date="2026-09-01",
            description="Sale for cash",
            lines=[
                {"account_id": cash["id"], "debit": "1000.00"},
                {"account_id": rev["id"], "credit": "1000.00"},
            ],
        )
        payload.update(overrides)
        return payload

    def test_post_without_reference_mints_next(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev),
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["reference"], f"JE-{_year()}-0001")

    def test_second_post_without_reference_increments(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        first = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev),
            format="json",
            **h,
        )
        self.assertEqual(first.status_code, 201, first.content)
        resp = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev),
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["reference"], f"JE-{_year()}-0002")

    def test_post_with_blank_reference_mints(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev, reference="   "),
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["reference"], f"JE-{_year()}-0001")

    def test_post_with_explicit_reference_preserved(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev, reference="JE-2026-0042"),
            format="json",
            **h,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["reference"], "JE-2026-0042")

    def test_next_reference_endpoint_returns_preview_without_consuming(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        resp = self.client.get(
            reverse("journalentry-next-reference"), **h
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["reference"], f"JE-{_year()}-0001")
        resp2 = self.client.get(
            reverse("journalentry-next-reference"), **h
        )
        self.assertEqual(resp2.data["reference"], f"JE-{_year()}-0001")
        create = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev),
            format="json",
            **h,
        )
        self.assertEqual(create.status_code, 201, create.content)
        self.assertEqual(create.data["reference"], f"JE-{_year()}-0001")

    def test_stale_preview_save_gets_next_free_reference(self):
        h = self.admin_h()
        cash, rev = self._make_accounts(h)
        preview = self.client.get(
            reverse("journalentry-next-reference"), **h
        )
        self.assertEqual(preview.data["reference"], f"JE-{_year()}-0001")
        rival = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev, reference=f"JE-{_year()}-0001"),
            format="json",
            **h,
        )
        self.assertEqual(rival.status_code, 201, rival.content)
        late = self.client.post(
            reverse("journalentry-list"),
            self._payload(cash, rev),
            format="json",
            **h,
        )
        self.assertEqual(late.status_code, 201, late.content)
        self.assertEqual(late.data["reference"], f"JE-{_year()}-0002")
