# Plan - Automatic Customer Code on Create

**Feature**: 013-auto-customer-code
**Created**: 2026-09-14
**Status**: Draft
**Input**: "from sales module when create customer make code automatic not user input"

## Phase 0 - Research (summary)

### Decisions

- **Where is the code minted**: backend, in `CustomerSerializer`/a tenant-scoped service at POST time. Single source of truth; the frontend never guesses.
- **Format**: `CUS-{seq}` per tenant, `seq` = max numeric suffix of existing tenant customer codes + 1 (or `1` when none). Uses the existing per-tenant uniqueness constraint unchanged.
- **Collision strategy**: compute from max(suffix)+1; if the resulting code already exists (race with user-entered code), increment. Loop bounded; identical to Feature 012 document-number handling.
- **Frontend change**: `CustomerModal` create form drops the `Code *` required input. On **edit**, code stays read-only & never regenerated.
- **Immutability**: existing customer codes untouched; no migration of old rows; schema unchanged.

### Context

- `Customer.code`: CharField(50), per-tenant unique (`unique_customer_code_per_tenant`).
- `CustomerSerializer.create` currently requires `code` (manual input). Will change to auto-generate on create.
- `CustomerModal.jsx` currently has `<Input label="Code *" ... required />`.

## Phase 1 - Design

### Implementation Plan v1

| Step | Task-type | File(s) | Change |
|------|-----------|---------|--------|
| 1 | backend | `apps/sales/serializers.py` | Add code-minting in `create`: if `code` blank → `CUS-{next}` |
| 2 | backend | `apps/sales/services.py` | Extract `_next_customer_code(tenant)` helper (max suffix + 1) |
| 3 | backend | `apps/sales/tests/` | Tests: auto code on create, unique per tenant, collision-safe, edit preserves code |
| 4 | frontend | `CustomerModal.jsx` | Remove `Code *` input on create; code read-only on edit |
| 5 | frontend | `CustomersPage.jsx` | Create → no code field in payload; list still shows auto code |

### Data Model (no migration)

No schema changes. `Customer` unchanged. Only the **create path** behavior changes.

### Contracts

- `POST /api/v1/sales/customers/` with `{"name": ...}` (no `code`) → 201, customer with auto `code`.
- `POST ...` with `{"code": "CUS-5", ...}` still respected (manual code still allowed).
- `PATCH .../{id}/` → code never regenerated/blanked.
- List `GET .../customers/` → includes `code`.

## Success Criteria

- SC-001: creating without a code returns a non-blank, tenant-unique auto code 100% of the time.
- SC-002: metric: 0 duplicate-code JEs / 0 tenant collisions in tests + regressions stay green (367→new count).
- SC-003: edit never changes the code (regression proves).

## Assumptions

- Manual user-entered codes remain supported (authors can still supply one).
- Only blank create is auto-minted.
- Existing rows keep codes as-is.

## Open Questions

- Prefer `CUS-0001` zero-padded or `CUS-1` non-padded? (Default chosen: `CUS-{n}` non-padded unless tenant already uses padding — implementation reads max suffix and preserves its padding style.)
