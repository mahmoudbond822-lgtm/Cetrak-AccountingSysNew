# Quickstart: Auto Invoice Number

**Feature**: `016-auto-invoice-number` | **Date**: 2026-09-16

Validates the feature end-to-end on both invoice sides. Details live in [data-model.md](./data-model.md) and [contracts/invoice-create.md](./contracts/invoice-create.md); no code bodies here.

## Prerequisites

- Backend deps installed; test settings module `config.settings.test`.
- Frontend deps installed (`frontend/`).
- A tenant with an admin user plus one customer and one vendor (test harness creates these per test).

## Backend validation

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
py -m pytest apps/sales/tests/test_auto_invoice_number.py apps/purchases/tests/test_auto_invoice_number.py -q
# Expected: all pass — POST without number → INV-0001 then INV-0002 per type; edit ignores number; per-business independence; explicit duplicate → 400
```

```powershell
py -m pytest apps/ -q
# Expected: no regressions vs baseline (381 passed, 1 skipped)
```

```powershell
py manage.py makemigrations --check --dry-run
# Expected: "No changes detected" (behavior-only change)
```

## Frontend validation

```powershell
cd frontend
npm run build
# Expected: clean build
```

Manual browser check per side (restart the dev server first if it predates this change):

1. Open Sales → Invoices → New Invoice (then Purchases → Purchase Invoices → New).
2. Confirm the Number field is visible, disabled, showing `INV-0001` (or the next free number of that type).
3. Save a valid invoice with lines → success, no "number required" error; the list shows the new invoice with that number.
4. Open New again → Number shows the next value (`INV-0002`).
5. Edit a draft (change dates/lines) → Number is visible but not editable and unchanged.
6. Post an invoice → journal reference embeds the minted number as today.

## Contract spot-checks (see contracts/invoice-create.md)

- POST without `number` → `201` with minted `number` (per-type sequence).
- POST with explicit `number` → respected; repeat same number same type → `400`, no new row.
- PATCH with `number` → `200`, original number unchanged (submitted value ignored).
