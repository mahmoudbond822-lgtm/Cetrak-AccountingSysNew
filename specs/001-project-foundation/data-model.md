# Data Model: Project Foundation

## BaseModel (Abstract)

Provides common audit fields. Used by Tenant and User (global entities with no tenant FK).

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key, auto-generated |
| created_at | DateTime | Auto-set on creation |
| updated_at | DateTime | Auto-updated on modification |

## TenantScopedModel (Abstract, inherits BaseModel)

Adds tenant FK for tenant-isolated entities. Used by all tenant-scoped business models (Membership, Invitation, future accounting entities).

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key (inherited) |
| tenant | UUID (FK → Tenant) | Nullable, CASCADE on delete |
| created_at | DateTime | Auto-set (inherited) |
| updated_at | DateTime | Auto-updated (inherited) |

## Tenant (inherits BaseModel)

Represents a company/organization. Has no tenant_id — it is the tenant root.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| name | String(255) | NOT NULL |
| status | Enum | Active, Suspended, Cancelled — default Active |

**Indexes**: None beyond PK

## User (inherits BaseModel)

An individual person who can access the system. Global entity — no tenant FK.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| email | String(254) | UNIQUE, NOT NULL |
| password | String(128) | NOT NULL (hashed with bcrypt) |
| display_name | String(255) | NULLABLE |
| status | Enum | Active, Invited/Pending, Disabled — default Active |

**Indexes**: email (unique)

**Validation**: Email format validated on create/update. Password minimum 8 characters with bcrypt hashing.

## Membership (inherits TenantScopedModel)

Links a User to a Tenant with a specific role.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID (FK → User) | NOT NULL, CASCADE on delete |
| tenant | UUID (FK → Tenant) | NOT NULL, CASCADE on delete |
| role | Enum | Admin, Accountant, Manager — default Accountant |

**Unique Constraint**: (user_id, tenant_id) — one membership per user per tenant

**Indexes**: (user_id, tenant_id) unique; tenant_id

## Invitation (inherits TenantScopedModel)

Represents a pending invitation from an admin to a new member.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant | UUID (FK → Tenant) | NOT NULL, CASCADE on delete |
| email | String(254) | NOT NULL |
| role | Enum | Accountant, Manager — default Accountant |
| token | String(64) | UNIQUE, NOT NULL (secure random token) |
| expires_at | DateTime | NOT NULL (default 7 days from creation) |
| accepted_at | DateTime | NULLABLE (set when accepted) |

**Indexes**: token (unique); email; tenant_id

## Entity Relationships

```text
BaseModel (abstract)
├── Tenant (no tenant_id — tenant root)
├── User (no tenant_id — global auth identity)
└── TenantScopedModel (abstract, adds tenant FK)
    ├── Membership
    └── Invitation

Tenant 1──* Membership *──1 User
  │
  │
  1──* Invitation
```

## State Transitions

### User States

```text
Invited/Pending ──(register)──→ Active
Active ──(admin disables)──────→ Disabled
Disabled ──(admin re-enables)──→ Active
```

### Tenant States

```text
Active ──(suspend)──→ Suspended ──(cancel)──→ Cancelled
Active ──(cancel)───→ Cancelled
Suspended ──(reactivate)──→ Active
```

### Invitation States (implicit)

```text
Pending ──(accepted)──→ Accepted (accepted_at set)
Pending ──(expired)───→ Expired (past expires_at)
```

## Design Notes

- **Two abstract bases**: `BaseModel` for global entities (Tenant, User), `TenantScopedModel` for tenant-scoped entities (Membership, Invitation, future accounting models). This enforces Constitution Article I (every table must have tenant_id) without requiring the Tenant model to reference itself.
- **User model is global** (inherits BaseModel, no tenant_id) because a user can belong to multiple tenants. Authentication is tenant-agnostic.
- **Membership scopes users to tenants** and is the primary authorization mechanism.
- **Invitation tokens** are single-use with a 7-day expiry. No separate model needed for password reset tokens — Django's built-in PasswordResetTokenGenerator handles those.
- **Soft-delete** for Cancelled tenants: a `cancelled_at` field or simply the status field suffices. Data is preserved for legal/audit purposes.
