# Data Model: Multi-Tenancy Hardening

**Phase**: 1 — Design

**Date**: 2026-06-18

## Schema Changes

### Invitation (via TenantScopedModel)

| Change | Current | New | Details |
|--------|---------|-----|---------|
| `tenant` FK nullability | `null=True` | `null=False` | FK to `core.Tenant`. Enforced at DB level. |

**Migration**: `accounts` — `ALTER COLUMN tenant_id SET NOT NULL`

**Data cleanup**: Run before migration — any Invitation with `tenant_id IS NULL` must be deleted or assigned to a tenant.

### Membership

| Change | Current | New | Details |
|--------|---------|-----|---------|
| `tenant` FK index | No dedicated index | `db_index=True` | FK to `core.Tenant`. |

**Migration**: `accounts` — `CREATE INDEX accounts_membership_tenant_id ON accounts_membership (tenant_id)`

**Rationale**: The existing `unique_user_tenant_membership` constraint creates a composite B-tree on `(user_id, tenant_id)`. PostgreSQL can use the leading column `user_id` for equality lookups, but a `WHERE tenant_id = X` query cannot efficiently use this index because `tenant_id` is the second column. A dedicated single-column index on `tenant_id` is needed for all tenant-filtered queries (list members, admin count check, member removal).

## Existing Entities (unchanged, reference only)

### Tenant (core.Tenant)

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, auto-generated |
| name | VARCHAR(255) | Required |
| status | VARCHAR(20) | Choices: Active, Suspended, Cancelled; defaults to Active |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

### Membership (accounts.Membership)

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, auto-generated |
| user | FK → User | Required, indexed via unique constraint |
| tenant | FK → Tenant | Required, **indexed after change** |
| role | VARCHAR(20) | Choices: Admin, Accountant, Manager |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

**Constraints**: `UNIQUE (user_id, tenant_id)` — a user can only belong to a tenant once.

### Invitation (accounts.Invitation)

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, auto-generated |
| tenant | FK → Tenant | **Required after change** (was nullable) |
| email | VARCHAR(254) | Required |
| role | VARCHAR(20) | Choices: Accountant, Manager |
| token | VARCHAR(64) | Unique, Required |
| expires_at | DateTime | Required |
| accepted_at | DateTime | Nullable |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

**Indexes**: `token`, `email`, `tenant_id`
**Constraints**: `UNIQUE (email, tenant_id)` — only one pending invitation per email per tenant.

### TenantScopedModel (abstract base)

| Field | Type | Constraints |
|-------|------|-------------|
| tenant | FK → Tenant | **Required** (`null=False` after change, previously nullable) |
| id | UUID | PK |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |
