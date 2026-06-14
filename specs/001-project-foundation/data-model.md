# Data Model: Project Foundation

## BaseEntity (Abstract)

Used by all models to enforce multi-tenancy and audit fields.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key, auto-generated |
| tenant_id | UUID (FK → Tenant) | NOT NULL (except Tenant model itself) |
| created_at | DateTime | Auto-set on creation |
| updated_at | DateTime | Auto-updated on modification |

## Tenant

Represents a company/organization.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| name | String(255) | NOT NULL |
| status | Enum | Active, Suspended, Cancelled — default Active |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Indexes**: None beyond PK

## User

An individual person who can access the system.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| email | String(254) | UNIQUE, NOT NULL |
| password | String(128) | NOT NULL (hashed with bcrypt) |
| display_name | String(255) | NULLABLE |
| status | Enum | Active, Invited/Pending, Disabled — default Active |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Indexes**: email (unique)

**Validation**: Email format validated on create/update. Password minimum 8 characters with bcrypt hashing.

## Membership

Links a User to a Tenant with a specific role.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID (FK → User) | NOT NULL, CASCADE on delete |
| tenant_id | UUID (FK → Tenant) | NOT NULL, CASCADE on delete |
| role | Enum | Admin, Accountant, Manager — default Accountant |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Unique Constraint**: (user_id, tenant_id) — one membership per user per tenant

**Indexes**: (user_id, tenant_id) unique; tenant_id

## Invitation

Represents a pending invitation from an admin to a new member.

| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID (FK → Tenant) | NOT NULL, CASCADE on delete |
| email | String(254) | NOT NULL |
| role | Enum | Accountant, Manager — default Accountant |
| token | String(64) | UNIQUE, NOT NULL (secure random token) |
| expires_at | DateTime | NOT NULL (default 7 days from creation) |
| accepted_at | DateTime | NULLABLE (set when accepted) |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Indexes**: token (unique); email; tenant_id

## Entity Relationships

```text
Tenant 1──* Membership *──1 User
  │                        │
  │                        │
  1──* Invitation          │
                           │
                          (global — no tenant_id)
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

- **User model is global** (no tenant_id) because a user can belong to multiple tenants. Authentication is tenant-agnostic.
- **Membership scopes users to tenants** and is the primary authorization mechanism.
- **Invitation tokens** are single-use with a 7-day expiry. No separate model needed for password reset tokens — Django's built-in PasswordResetTokenGenerator handles those.
- **Soft-delete** for Cancelled tenants: a `cancelled_at` field or simply the status field suffices. Data is preserved for legal/audit purposes.
