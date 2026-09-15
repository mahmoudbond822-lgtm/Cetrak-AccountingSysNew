# Data Model: Auto Customer Code

**Feature**: `014-auto-customer-code` | **Date**: 2026-09-15

## Overview

This feature implements automatic customer code minting for the customer creation flow. The backend mints a unique, zero-padded code at the moment of creation (POST) and stores it in the `Customer` model. The create dialog displays the next available code in a disabled (non-editable) field as a hint. On save, the system assigns the next free code, skipping any colliding values.

## Customer Model

### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|--------------|
| `id` | UUID | Unique identifier | Primary key |
| `name` | String | Customer name | Required |
| `email` | Email | Contact email | Optional |
| `phone` | Phone | Contact phone | Optional |
| `address` | Text | Physical address | Optional |
| `is_active` | Boolean | Account status | Default: true |
| `code` | String | Unique customer code | Required, zero-padded `CUS-XXXXX` |
| `created_at` | DateTime | Creation timestamp | Auto-set |
| `updated_at` | DateTime | Last update timestamp | Auto-set |

### Code Field Details

- **Format**: `CUS-` + zero-padded 4-digit sequence (e.g., `CUS-0001`, `CUS-0002`)
- **Uniqueness**: Per-business (tenant) only; globally unique within each tenant
- **Generation**: Deterministic: `max(existing_codes) + 1`, with collision resolution
- **Assignment Time**: At POST (create) time; never edited after creation
- **Collision Strategy**: Max suffix + 1; if candidate exists (race with manual entry), increment until free
- **Persistence**: Stored in `Customer.code` (CharField(50)), existing unique constraint retained

## Sequence Logic

1. **Initial**: First customer in a business → `CUS-0001`
2. **Subsequent**: Each new customer gets `max(existing) + 1`
3. **Collisions**: If `CUS-0005` already exists (manually entered), next becomes `CUS-0006`
4. **Deletion**: Gaps are preserved; no backward filling

## Example Flow

1. User opens Create Customer → sees `CUS-0001` (disabled, read-only)
2. User enters name, clicks Save
3. Server calculates next code (`CUS-0001`)
4. If `CUS-0001` is taken (race), tries `CUS-0002`, etc.
5. Server creates `Customer(code: "CUS-0001")`
6. Response: `201 Created { "id": "...", "name": "...", "code": "CUS-0001" }`
7. Client receives code and proceeds with customer details
8. Future edits preserve the existing code (never blanked)

## Relationships

- **One-to-Many**: Customer → (many) Orders, Invoices, Reports
- **Many-to-One**: Order → Customer (foreign key `customer_id`)
- **Unique Constraint**: `Customer.code` + `tenant_id` combination

## Migration Impact

- **No schema migration** required – the `Customer` model already has a `code` field (CharField(50))
- **No new endpoints** – existing `GET /customers`, `POST /customers`, `PUT /customers/{id}` suffice
- **No breaking changes** – existing code values remain intact; new code is additive

## Validation Rules

- **Code format**: Must match `^CUS-\d{4}$` (zero-padded 4 digits)
- **Uniqueness**: Enforced at application level (DB unique constraint)
- **Non-negative**: Monotonic increase within each tenant
- **Cross-tenant isolation**: Tenant IDs isolated; codes never cross tenants

## Edge Cases

- **First customer**: Gets `CUS-0001`
- **Manual code collision**: System skips to next free code
- **Rapid successive saves**: Race condition handled by max-suffix + loop
- **Cancelled/abandoned drafts**: Consume nothing; no reservation held
- **Deleted customers**: Their codes are never reused; gaps preserved

## Testing Approach

- **Unit tests**: Verify code minting logic, collision resolution, edit preservation
- **Integration tests**: End-to-end create flow with mocked DB
- **Concurrency tests**: Parallel saves in same tenant to verify collision handling
- **Edge case tests**: Empty code submission, whitespace-only, negative indices

## Assumptions

- Tenant identification is via `tenant_id` (standard multi-tenancy pattern)
- Customer creation is the sole place where code is assigned
- No bulk import of customers with pre-assigned codes (would require migration)
- Existing `unique_customer_code_per_tenant` constraint is sufficient

## References

- **Spec**: [spec.md](specs/014-auto-customer-code/spec.md)
- **Constitution**: [constitution.md](.specify/memory/constitution.md)
- **Research**: [research.md](specs/013-auto-customer-code/research.md)
- **Related**: 013-auto-customer-code (identical feature, already implemented)
