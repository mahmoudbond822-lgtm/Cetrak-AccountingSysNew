# Implementation Report: Auto Journal Entry Code

**Branch**: `014-auto-journal-entry-code` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Summary

Creating a manual journal entry used to fail whenever the user left the Reference field empty — the serializer rejected it with a validation error, blocking the whole journal entry flow. This feature makes the system own the reference: the backend mints the next per-tenant, per-year code (`JE-2026-0001`, +1 per saved entry) at save time, and the create form shows that next code in a visible but read-only field. The dialog preview is a non-binding hint; authoritative assignment happens at save, skipping collisions, scoped per business, and immutable on edit.

## What Changed

### Backend

- **`backend/apps/accounting/services.py`** — `JournalEntryService.next_reference(year=None)`: computes `JE-YYYY-NNNN` scoped to the tenant and the current year. It scans the highest numeric suffix among that tenant's `JE-YYYY-*` references, then walks up to 100 candidates skipping any that already exist (mirrors the established `SalesInvoiceService.next_number()` / `VendorService` pattern, with an added year component). `create_entry()` now takes an optional `reference`; a blank or missing value mints the next one. Added `timezone` import.
- **`backend/apps/accounting/serializers.py`** — `JournalEntrySerializer.reference` is now `required=False, allow_blank=True, allow_null=True`, and the serializer's `create()` mints via the service when the value is blank so the model field is never empty.
- **`backend/apps/accounting/views.py`** — the create view passes `serializer.validated_data.get("reference")` (no more KeyError on a missing field), and a new `GET /api/v1/accounting/journal-entries/next-reference/` action returns the next code for the form preview without consuming it.
- **`backend/apps/accounting/tests/test_auto_journal_entry_code.py`** — 18 new tests (service-level + API-level) covering sequencing, format, blank/missing/explicit values, collision skip, legacy non-numeric and prior-year references, cross-tenant independence, preview non-consumption, and the stale-preview fallthrough.

### Frontend

- **`frontend/src/services/accountingService.js`** — added `getNextJournalReference()`.
- **`frontend/src/components/accounting/journal/JournalEntryForm.jsx`** — the Reference field is now a read-only preview that fetches its value from the new endpoint on mount; `reference` was removed from the create payload so the backend assigns authoritatively; the unsaved-changes guard no longer counts the auto field.
- **`frontend/src/components/sales/customers/CustomerModal.jsx`** — removed a stray unused `useEffect` import that predated this feature and was the single source of a new lint error.
- **`frontend/src/components/accounting/journal/JournalLineRow.jsx`** — pre-existing working-tree fix (batching debit/credit mutual exclusion into one state update) kept as-is.

## Contract

- **Request** (reference now optional):
  ```json
  POST /api/v1/accounting/journal-entries/
  { "date": "2026-09-19", "description": "Opening entry", "lines": [ {"account_id": "...", "debit": "1000.00"}, {"account_id": "...", "credit": "1000.00"} ] }
  ```
- **Response** (201): the persisted `reference` is returned, e.g. `"JE-2026-0001"`.
- **Preview**: `GET /api/v1/accounting/journal-entries/next-reference/` → `{ "reference": "JE-2026-0001" }` — read-only, never consumes a code.
- Explicit references are still honored when provided; uniqueness per tenant is enforced by the existing `unique_reference_per_tenant` constraint. Entries remain immutable (405 on PUT/PATCH/DELETE), which already satisfies the read-only-after-creation requirement.

## Deviations from Plan

- The plan's source layout referenced `backend/apps/journal/` and `JournalService`/`JournalEntryForm.jsx` paths that do not exist in this repo. The real code lives in `backend/apps/accounting/` (`JournalEntryService`) and `frontend/src/components/accounting/journal/`. Implementation followed the real structure; intent is identical.
- The plan did not call out a preview endpoint (it implied deriving the next code client-side from the list, as customer/vendor do). A dedicated read-only endpoint was added instead because the journal list is date-filterable, so a client-side derivation from the visible rows would produce wrong previews — the endpoint keeps the hint accurate and keeps the year logic server-side. This is additive and does not change any existing contract.

## Verification

- **Backend**: `py -m pytest apps/ -q` → **421 passed, 1 skipped** (baseline 403 passed, 1 skipped; +18 new). Command: `cd backend; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q`
- **Migrations**: `py manage.py makemigrations --check --dry-run` → "No changes detected" (behavior-only change, no schema impact).
- **Frontend build**: `npm run build` clean (405.21 kB JS / 111.50 kB gzip).
- **Frontend lint**: `npm run lint` → 18 problems, exactly the pre-existing baseline (verified by stashing all changes and diffing the two reports; zero new problems from this feature).

## Readiness

Feature complete against spec `014-auto-journal-entry-code`. All four user stories and their acceptance scenarios are covered by the new tests and the manual quickstart path (open form → disabled preview → save → list shows assigned code → reopen shows next). No migration, no contract break, no new lint debt.
