# Data Model: Auto Customer Code

**Feature**: `013-auto-customer-code` | **Date**: 2026-09-14

No schema changes. This feature changes **who supplies `Customer.code`** (system-minted at create vs. user-typed), not the entity shape.

## Entities

### Customer (unchanged schema)

| Attribute | Meaning | Rule in this feature |
|-----------|---------|----------------------|
| `code` | Per-business unique identifier, e.g. `CUS-0001` | System-minted at create when blank/missing; never edited after; skipped on collision |
| `name` | Customer name | Required, user-entered (unchanged) |
| `email`, `phone`, `address`, `tax_id` | Contact details | Optional, user-entered (unchanged) |
| `is_active` | Active flag | Unchanged |

- **Identity**: (`business`, `code`) unique — existing `unique_customer_code_per_tenant` constraint, kept as-is.
- **Lifecycle**: create (code minted once) → edit (code preserved, read-only) → delete (code never reused; numbering keeps moving forward).
- **State transitions**: none added.

### Business / Tenant (unchanged)

- Owns customers and their code sequence. Each business's numbering is independent: first customer → `CUS-0001` regardless of other businesses.

## Validation rules (from spec FR-001…FR-007)

- Create accepts missing/blank/whitespace code → mint path (no "code required" rejection).
- Minted code matches `CUS-NNNN` (zero-padded 4-digit), unique within the business, collision-skipped.
- Edit path ignores any submitted code value (existing code preserved).
- All reads/writes filtered by business (tenant isolation, constitution principle I).

## Scale

- One indexed max-suffix scan per customer create; no volume concern for this entity's expected size.
