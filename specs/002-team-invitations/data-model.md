# Data Model: Team Invitations

## Invitation (inherits TenantScopedModel)

Represents a pending invitation from an admin to a new team member.

| Field | Type | Constraints |
|-------|------|-------------|
| tenant | UUID (FK → Tenant) | NOT NULL, CASCADE on delete (inherited from TenantScopedModel) |
| email | String(254) | NOT NULL |
| role | Enum | Accountant, Manager — default Accountant (Admin role not available for invitation) |
| token | String(64) | UNIQUE, NOT NULL (secure random token) |
| expires_at | DateTime | NOT NULL (default 7 days from creation) |
| accepted_at | DateTime | NULLABLE (set when invitation is accepted) |

**Indexes**: token (unique), email, tenant_id, (email, tenant_id) unique

**Validation**:
- Token must be unique across all invitations
- An email can only have one pending invitation per tenant (unique constraint on email + tenant where accepted_at is null — application-level)
- Role must be Accountant or Manager (not Admin)

## Membership (existing, modified)

**New validation rules**:
- Cannot change the last admin's role to a non-admin role
- Cannot remove the last admin from the tenant
- Role change removed the constraint; only Admin can have been the last admin

## Existing Entities (unchanged)

| Entity | Description |
|--------|-------------|
| User | An individual person who can access the system. Authenticated via JWT. |
| Tenant | A company or organization. Contains isolated data for all users. |
| Membership | Links a User to a Tenant with a specific role. |

## Entity Relationships

```text
TenantScopedModel (abstract)
└── Invitation (tenant FK, email, role, token, expires_at, accepted_at)

Tenant 1──* Invitation
Tenant 1──* Membership *──1 User
```

## State Transitions

### Invitation States

```text
Pending ──(accepted)──→ Accepted (accepted_at set, membership created)
Pending ──(expired)──→ Expired (past expires_at — registration rejected)
Pending ──(cancelled)──→ Cancelled (admin cancelled — token invalidated)
```

Status is implicit (derived from expires_at and accepted_at fields):
- `accepted_at` is null AND `expires_at` is in the future → Pending
- `accepted_at` is set → Accepted
- `expires_at` is in the past AND `accepted_at` is null → Expired
- Explicit `cancelled_at` field could be added if audit trail needed; for MVP, DELETE removes the record

## Design Notes

- Invitation inherits `TenantScopedModel` so it automatically has tenant isolation (Constitution Article I).
- Token is a purely random opaque string — no JWT or encoding needed.
- The invitation acceptance creates a Membership record linking the user to the tenant.
- For existing users (already registered), no new registration occurs — the Membership is created directly upon invitation acceptance.
- The `(email, tenant_id)` unique constraint prevents duplicate pending invitations for the same email in the same tenant.
