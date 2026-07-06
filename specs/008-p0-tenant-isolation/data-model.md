# Data Model: P0 Tenant Isolation

## Tenant

Represents a customer workspace or company boundary.

**Relevant Fields**:

- `id`: Stable tenant identifier
- `name`: Tenant display name
- `status`: Tenant lifecycle state

**Relationships**:

- Owns accounting records through tenant-scoped models
- Has memberships connecting users to tenant roles

**Validation Rules**:

- Only the active tenant context may be used when accepting accounting references for a request
- Records from another tenant are inaccessible even if the user knows their identifiers

## Accounting User

Represents an authenticated user operating within one active tenant context.

**Relevant Fields**:

- `id`: Stable user identifier
- `email`: Login identity
- `memberships`: Tenant-specific roles

**Relationships**:

- May belong to one or more tenants
- May perform accounting actions only when their active tenant grants accounting access

**Validation Rules**:

- Membership in one tenant does not permit accounting references from another tenant
- Users with multiple memberships may only reference records from the active tenant for the current action

## Account

Represents a tenant-owned financial account.

**Relevant Fields**:

- `id`: Stable account identifier
- `tenant`: Owning tenant
- `name`: Account name
- `type`: Account category
- `parent`: Optional parent account
- `is_active`: Whether the account is available for normal use

**Relationships**:

- Belongs to exactly one tenant
- May have a parent account from the same tenant
- May be referenced by journal entry lines from the same tenant

**Validation Rules**:

- A parent account reference must belong to the active tenant
- A journal line account reference must belong to the active tenant
- Inaccessible accounts must be rejected without exposing their details

## Journal Entry

Represents a tenant-owned accounting transaction.

**Relevant Fields**:

- `id`: Stable journal entry identifier
- `tenant`: Owning tenant
- `date`: Accounting date
- `reference`: Tenant-specific reference
- `description`: Entry description
- `posted`: Posting state
- `posted_at`: Posting timestamp when posted

**Relationships**:

- Belongs to exactly one tenant
- Contains two or more journal entry lines
- All referenced line accounts must belong to the same active tenant

**Validation Rules**:

- Entry creation must be rejected if any line references an inaccessible account
- Mixed-tenant entries must not be partially saved
- Rejected attempts must not alter balances, ledgers, reports, or entry counts

## Journal Entry Line

Represents one debit or credit line inside a journal entry.

**Relevant Fields**:

- `id`: Stable line identifier
- `entry`: Owning journal entry
- `account`: Referenced account
- `debit`: Debit amount
- `credit`: Credit amount
- `description`: Optional line description

**Relationships**:

- Belongs to one journal entry
- References one account from the same active tenant as the entry

**Validation Rules**:

- The referenced account must be accessible in the active tenant context
- A failed line reference invalidates the entire journal entry request
