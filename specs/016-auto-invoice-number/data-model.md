# Data Model: Auto Invoice Number

**Feature**: `016-auto-invoice-number` | **Date**: 2026-09-16

## Overview

This feature implements automatic invoice number minting for sales and purchase invoice creation, mirroring Features 014/015. The backend mints a unique, zero-padded number at draft creation (POST) and stores it in the invoice row. The create dialogs display the next available number in a disabled field as a hint. On save, the system assigns the next free number of that invoice type, skipping collisions. Numbers lock at creation — drafts stay editable in all other respects.

## Invoice Models

### SalesInvoice (fields relevant to this feature)

| Field | Type | Description | Constraints |
|-------|------|-------------|--------------|
| `id` | UUID | Unique identifier | Primary key |
| `number` | String | Invoice number | Required at DB level, auto-minted when blank; unique per tenant (`unique_invoice_number_per_tenant`) |
| `customer` | FK | Billing customer | Required, tenant-scoped, must be active |
| `status` | Enum | Draft / Posted | Default Draft; guards edit/delete/post transitions (untouched) |

### PurchaseInvoice (fields relevant to this feature)

| Field | Type | Description | Constraints |
|-------|------|-------------|--------------|
| `id` | UUID | Unique identifier | Primary key |
| `number` | String | Invoice number | Required at DB level, auto-minted when blank; unique per tenant (per-table constraint) |
| `vendor` | FK | Supplying vendor | Required, tenant-scoped |
| `status` | Enum | Draft / Posted | Default Draft; guards edit/delete/post transitions (untouched) |

### Number Field Details (both types)

- **Format**: `INV-` + zero-padded 4-digit sequence (e.g., `INV-0001`, `INV-0002`)
- **Uniqueness**: Per business per invoice type (existing per-table constraints retained)
- **Sequences**: Independent — sales runs its own `INV-` run, purchase runs its own; the same value may exist once per type
- **Generation**: Deterministic per type: `max(existing INV- suffix for that type) + 1`, with collision resolution
- **Assignment Time**: At draft POST; never changed afterwards (draft or posted)
- **Collision Strategy**: Max suffix + 1; taken candidates increment until free
- **Explicit numbers**: Honored as-is when unused; duplicates of the same type rejected (`400 "Invoice number already exists"`, unchanged)
- **Legacy coexistence**: Pre-existing numbers in other formats untouched and excluded from the `INV-` suffix scan insofar as they carry no `INV-` numeric suffix

## Sequence Logic (per type, per business)

1. **Initial**: First invoice of the type → `INV-0001`
2. **Subsequent**: Each new invoice of the type gets `max(existing type suffix) + 1`
3. **Collisions**: If `INV-0005` already exists (manually entered), next becomes `INV-0006`
4. **Deletion**: Draft deletes preserve gaps; no backward filling

## Example Flow (sales; purchase identical)

1. User opens New Invoice → sees `INV-0001` (disabled, read-only)
2. User picks customer, dates, lines; clicks Save
3. Server calculates next sales number (`INV-0001`)
4. If taken (race), tries `INV-0002`, etc.
5. Server creates draft `SalesInvoice(number: "INV-0001")`
6. Response: `201 Created { "id": "...", "number": "INV-0001", ... }`
7. Posting later derives `SALES-INV-INV-0001` journal reference as today
8. Future edits (draft) preserve the number; the field is read-only

## Relationships

- **SalesInvoice → Customer** (FK, tenant-scoped); **PurchaseInvoice → Vendor** (FK, tenant-scoped)
- **Invoice → lines** (one-to-many, created in the same transaction — untouched)
- **Invoice → journal entry** on post (reference embeds the stored number — untouched)
- **Unique Constraints**: `(tenant, number)` per invoice table, retained

## Migration Impact

- **No schema migration** required — both tables already have `number` CharField(50)
- **No new endpoints** — existing invoice list/create/update routes suffice
- **No breaking changes** — existing numbers intact; explicit-number callers unaffected

## Validation Rules

- **Number format**: Auto-minted numbers match `^INV-\d{4}$`; legacy manual numbers keep their format
- **Uniqueness**: Enforced per business per type (DB unique constraints)
- **Monotonic**: Non-decreasing within each business per type
- **Cross-tenant isolation**: Sequences never cross tenants
- **Immutability**: Number ignored on update in both draft and posted states

## Edge Cases

- **First invoice of type**: Gets `INV-0001`
- **Manual number collision**: System skips to next free number
- **Rapid successive saves**: Race handled by max-suffix + loop (residual DB race still surfaces the existing 400, as today)
- **Cancelled/abandoned drafts**: Consume nothing
- **Deleted drafts**: Numbers never reused
- **Cross-type same value**: Allowed by design (separate tables, namespaced journal refs)

## Testing Approach

- **Unit/integration tests** (per-app `test_auto_invoice_number.py`): sequence, `INV-` prefix, blank-mint, locked-on-edit, cross-tenant independence, stale-preview, explicit-duplicate rejection
- **Regression**: Full `apps/` suite stays green; all existing explicit-number invoice tests unchanged
- **Concurrency**: Stale-preview path covered by sequential simulation (explicit squat then mint)

## Assumptions

- Tenant identification via `tenant_id` (standard multi-tenancy pattern)
- Draft creation is the sole place where numbers are assigned
- No bulk import of invoices with pre-assigned numbers (would require migration)
- Existing per-table unique constraints are sufficient

## References

- **Spec**: [spec.md](./spec.md)
- **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
- **Research**: [research.md](./research.md)
- **Related**: 014-auto-customer-code, 015-auto-vendor-code (mirrored features, implemented)
