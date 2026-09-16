# Quickstart: Auto Vendor Code

**Feature**: `015-auto-vendor-code` | **Date**: 2026-09-16

Validates the feature end-to-end. Details live in [data-model.md](./data-model.md) and [contracts/vendor-create.md](./contracts/vendor-create.md); no code bodies here.

## Prerequisites

- Backend deps installed; test settings module `config.settings.test`.
- Frontend deps installed (`frontend/`).
- A tenant with an admin user (test harness creates these per test).

## Backend validation

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
py -m pytest apps/purchases/tests/test_auto_vendor_code.py apps/purchases/tests/test_vendors_api.py -q
# Expected: all pass — POST without code → VEN-0001 then VEN-0002; edit preserves code; per-business independence; existing vendor tests unbroken
```

```powershell
py -m pytest apps/ -q
# Expected: 375 passed, 1 skipped (no regressions)
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

Manual browser check (restart the dev server first if it predates this change):

1. Open Purchases → Vendors → Create Vendor.
2. Confirm the Code field is visible, disabled, showing `VEN-0001` (or the next free code).
3. Save with only a name → success, no "code required" error; the list shows the new vendor with that code.
4. Open Create again → Code shows the next value (`VEN-0002`).
5. Edit any vendor → Code is visible but not editable; changing the name preserves the code.

## Contract spot-checks (see contracts/vendor-create.md)

- POST without `code` → `201` with minted `code`.
- POST with explicit `code` → respected; repeat same code in same business → `200`, no new row.
- PATCH without `code` → `200`, original code unchanged.
