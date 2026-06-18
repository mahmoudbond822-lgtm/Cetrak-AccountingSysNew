# Data Model: Accounting Schema

**Phase**: 1 — Design

**Date**: 2026-06-18

## Entities

### Account

Represents a single account in the Chart of Accounts. Each account belongs to exactly one tenant and has exactly one of five types.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID (PK) | Auto-generated | Primary identifier |
| `tenant` | FK → core.Tenant | NOT NULL, indexed | Tenant scope (via TenantScopedModel) |
| `name` | CharField(255) | NOT NULL | Human-readable account name (e.g., "Cash", "Accounts Receivable") |
| `type` | CharField(20) | NOT NULL, enum | One of: `Asset`, `Liability`, `Equity`, `Revenue`, `Expense` |
| `parent` | FK → self | NULLABLE, indexed | Parent account for hierarchy; NULL = root account |
| `description` | TextField | NULLABLE | Optional description |
| `is_active` | BooleanField | Default: true | Soft-deactivation; accounts with journal entries cannot be deleted |
| `created_at` | DateTimeField | Auto now add | From BaseModel |
| `updated_at` | DateTimeField | Auto now | From BaseModel |

**Type Enum**:

| Value | Normal Balance | Description |
|-------|---------------|-------------|
| `Asset` | Debit | Resources owned by the entity |
| `Liability` | Credit | Obligations owed by the entity |
| `Equity` | Credit | Owner's interest in the entity |
| `Revenue` | Credit | Income earned by the entity |
| `Expense` | Debit | Costs incurred by the entity |

**Validation Rules**:

- An account with child accounts (`parent_id` references exist) cannot be deleted
- An account referenced by any `JournalEntryLine` cannot be deleted or have its `type` changed
- Tree depth is limited to 10 levels (enforced in application logic)
- Root accounts (parent=NULL) are allowed; a tenant must have at least one root account of each type before posting entries

---

### JournalEntry

Represents a single financial transaction. Contains one or more lines. Must always be balanced (total debits = total credits). Immutable after creation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID (PK) | Auto-generated | Primary identifier |
| `tenant` | FK → core.Tenant | NOT NULL, indexed | Tenant scope (via TenantScopedModel) |
| `date` | DateField | NOT NULL | Transaction date |
| `description` | TextField | NOT NULL | Narrative description of the transaction |
| `reference` | CharField(255) | NOT NULL | External reference number (e.g., invoice number, check number) |
| `created_at` | DateTimeField | Auto now add | From BaseModel |
| `updated_at` | DateTimeField | Auto now | From BaseModel (unchanged, as entries are immutable — no updates expected) |

**Validation Rules**:

- `date` cannot be in the future (must be today or earlier)
- Must have at least two lines
- Total debits must equal total credits (balanced-entry rule enforced by DB CHECK constraint + application validation)
- Cannot be modified or deleted after creation (immutable)

---

### JournalEntryLine

A single line within a journal entry. References one account and contains either a debit or a credit amount (not both).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID (PK) | Auto-generated | Primary identifier |
| `entry` | FK → JournalEntry | NOT NULL, indexed | Parent journal entry; CASCADE on delete |
| `account` | FK → Account | NOT NULL, indexed | Account being debited or credited |
| `debit` | DecimalField(19,4) | Default: 0, ≥ 0 | Debit amount |
| `credit` | DecimalField(19,4) | Default: 0, ≥ 0 | Credit amount |
| `description` | TextField | NULLABLE | Line-level description (overrides entry description if set) |

**Validation Rules**:

- Exactly one of `debit` or `credit` must be non-zero (the other must be zero)
- `debit ≥ 0` and `credit ≥ 0` (non-negative amounts — direction is by field, not sign)
- `description` is optional; if null, the parent entry's description applies
- Cannot be modified or deleted individually (immutable through parent)

---

## Relationships

```text
Tenant (core_tenant)
   │
   ├──< Account (accounting_account)        # 1:N
   │      └──< Account.parent               # self-referencing; 1:N (parent → children)
   │
   └──< JournalEntry (accounting_journalentry)  # 1:N
           │
           └──< JournalEntryLine (accounting_journalentryline)  # 1:N
                   │
                   └──< Account              # N:1 (many lines can reference one account)
```

## Constraints

### Balanced-Entry CHECK Constraint

On `JournalEntry` table:

```sql
-- PostgreSQL function for balanced entry check
CREATE OR REPLACE FUNCTION check_entry_balanced(entry_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT ABS(
        COALESCE((SELECT SUM(debit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0) -
        COALESCE((SELECT SUM(credit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0)
    ) < 0.01;
$$ LANGUAGE SQL IMMUTABLE;

-- CHECK constraint using the function
ALTER TABLE accounting_journalentry
ADD CONSTRAINT balanced_entry_check
CHECK (check_entry_balanced(id));
```

### Other Constraints

- **Unique per tenant (account name)**: Tenant-level unique account names within the same parent (enforced at application layer).
- **Unique per tenant (reference)**: Journal entry reference numbers are unique per tenant (application-level).
- **Immutability**: No UPDATE or DELETE on `JournalEntry` or `JournalEntryLine` after creation (enforced at application layer; a DB trigger is optional for defense-in-depth).

## State Transitions

| Entity | States | Transitions |
|--------|--------|-------------|
| Account | Active ↔ Inactive (via `is_active`) | Active → Inactive (only if no unreconciled entries); Inactive → Active (always allowed) |
| JournalEntry | (none — immutable) | Created → exists forever |

Accounts have a soft lifecycle (active/inactive). Journal entries are append-only — once created, they cannot be changed.
