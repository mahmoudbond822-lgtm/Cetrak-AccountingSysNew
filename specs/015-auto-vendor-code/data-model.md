# Data Model: Auto Vendor Code

**Feature**: `015-auto-vendor-code` | **Date**: 2026-09-16

## Overview

This feature implements automatic vendor code minting for the vendor creation flow, mirroring Feature 014 (customer codes). The backend mints a unique, zero-padded code at the moment of creation (POST) and stores it in the `Vendor` model. The create dialog displays the next available code in a disabled (non-editable) field as a hint. On save, the system assigns the next free code, skipping any colliding values.

## Vendor Model

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|--------------|
| `id` | UUID | Unique identifier | Primary key |
| `name` | String | Vendor name | Required |
| `email` | Email | Contact email | Optional |
| `phone` | Phone | Contact phone | Optional |
| `address` | Text | Physical address | Optional |
| `tax_id` | String | Tax identifier | Optional |
| `is_active` | Boolean | Account status | Default: true |
| `code` | String | Unique vendor code | Required at DB level, auto-minted when blank |
| `created_at` | DateTime | Creation timestamp | Auto-set |
| `updated_at` | DateTime | Last update timestamp | Auto-set |

### Code Field Details

- **Format**: `VEN-` + zero-padded 4-digit sequence (e.g., `VEN-0001`, `VEN-0002`)
- **Uniqueness**: Per-business (tenant) only; globally unique within each tenant (`unique_vendor_code_per_tenant`)
- **Generation**: Deterministic: `max(existing_codes) + 1`, with collision resolution
- **Assignment Time**: At POST (create) time; never edited after creation
- **Collision Strategy**: Max suffix + 1; if candidate exists (race with manual entry), increment until free
- **Persistence**: Stored in `Vendor.code` (CharField(50)), existing unique constraint retained
- **Legacy coexistence**: Pre-existing codes in other formats (e.g., `V-001`) are untouched and excluded from the `VEN-` suffix scan only insofar as they carry no `VEN-` numeric suffix

## Sequence Logic

1. **Initial**: First vendor in a business → `VEN-0001`
2. **Subsequent**: Each new vendor gets `max(existing VEN- suffix) + 1`
3. **Collisions**: If `VEN-0005` already exists (manually entered), next becomes `VEN-0006`
4. **Deletion**: Gaps are preserved; no backward filling

## Example Flow

1. User opens Create Vendor → sees `VEN-0001` (disabled, read-only)
2. User enters name, clicks Save
3. Server calculates next code (`VEN-0001`)
4. If `VEN-0001` is taken (race), tries `VEN-0002`, etc.
5. Server creates `Vendor(code: "VEN-0001")`
6. Response: `201 Created { "id": "...", "name": "...", "code": "VEN-0001" }`
7. Client receives code and proceeds with vendor details
8. Future edits preserve the existing code (never blanked)

## Relationships

- **One-to-Many**: Vendor → (many) PurchaseInvoices
- **Unique Constraint**: `Vendor.code` + `tenant_id` combination (`unique_vendor_code_per_tenant`)
- **Protected**: `Vendor.invoices` uses `on_delete=PROTECT` — vendors with invoices cannot be deleted (deactivate instead), so their codes persist

## Migration Impact

- **No schema migration** required – the `Vendor` model already has a `code` field (CharField(50))
- **No new endpoints** – existing vendor list/create/update routes suffice
- **No breaking changes** – existing code values remain intact; new code is additive

## Validation Rules

- **Code format**: Auto-minted codes match `^VEN-\d{4}$` (zero-padded 4 digits); legacy manual codes keep whatever format they have
- **Uniqueness**: Enforced at application level (DB unique constraint)
- **Non-negative**: Monotonic increase within each tenant
- **Cross-tenant isolation**: Tenant IDs isolated; codes never cross tenants

## Edge Cases

- **First vendor**: Gets `VEN-0001`
- **Manual code collision**: System skips to next free code
- **Rapid successive saves**: Race condition handled by max-suffix + loop
- **Cancelled/abandoned drafts**: Consume nothing; no reservation held
- **Deleted vendors**: Their codes are never reused; gaps preserved

## Testing Approach

- **Unit tests** (`test_auto_vendor_code.py`): minting logic, `VEN-` prefix, blank-mint, edit preservation, cross-tenant independence
- **Integration tests**: End-to-end create flow (POST without code → 201 + code; explicit code → honored; duplicate explicit → 200 idempotent)
- **Concurrency tests**: Parallel saves in same tenant to verify collision handling
- **Regression**: Full `apps/` suite stays 375 passed / 1 skipped; existing `test_vendors_api.py` unchanged

## Assumptions

- Tenant identification is via `tenant_id` (standard multi-tenancy pattern)
- Vendor creation is the sole place where code is assigned
- No bulk import of vendors with pre-assigned codes (would require migration)
- Existing `unique_vendor_code_per_tenant` constraint is sufficient

## References

- **Spec**: [spec.md](./spec.md)
- **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
- **Research**: [research.md](./research.md)
- **Related**: 014-auto-customer-code (mirrored feature, already implemented)
