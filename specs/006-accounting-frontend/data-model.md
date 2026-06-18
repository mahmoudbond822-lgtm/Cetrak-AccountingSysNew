# Data Model: Accounting Frontend

No new backend models are needed. All entities were defined in [005-accounting-schema](../005-accounting-schema/spec.md). This document describes the data structures the frontend works with.

## Existing Backend Models

### Account

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `name` | string (255) | Display name |
| `type` | enum | Asset, Liability, Equity, Revenue, Expense |
| `parent_id` | UUID (nullable) | Self-referential FK for hierarchy |
| `description` | text (nullable) | Optional |
| `is_active` | boolean | Soft-delete flag |
| `children` | nested array | Populated recursively in tree view |

### JournalEntry

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `date` | date (ISO 8601) | Entry date |
| `description` | text | Transaction description |
| `reference` | string (255) | Unique per tenant |
| `lines` | nested array | 2+ journal entry lines |
| `total_debit` | decimal (19,4) | Computed (read-only) |
| `total_credit` | decimal (19,4) | Computed (read-only) |
| `line_count` | integer | Computed (read-only) |
| `created_at` | datetime | Read-only |

### JournalEntryLine

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `account_id` | UUID | FK to Account |
| `account_name` | string | Read-only (from Account) |
| `account_type` | string | Read-only (from Account) |
| `debit` | decimal (19,4) | Must be 0 if credit is set |
| `credit` | decimal (19,4) | Must be 0 if debit is set |
| `description` | text (nullable) | Optional line description |

## Frontend State Shapes

### Account Form (Create/Edit)

```typescript
{
  name: string,
  type: "Asset" | "Liability" | "Equity" | "Revenue" | "Expense",
  parent_id: string | null,
  description: string,
  is_active: boolean
}
```

### Journal Entry Form (Create)

```typescript
{
  date: string,          // YYYY-MM-DD
  description: string,
  reference: string,
  lines: Array<{
    account_id: string,
    debit: number | "",  // empty string before user input
    credit: number | ""
  }>
}
```

### Journal Line Row (in-memory form state)

```typescript
{
  id: number,            // temp client-side ID for key/order
  account_id: string | null,
  account_name: string,  // displayed after selection
  debit: number | "",
  credit: number | "",
  description: string
}
```

### Ledger Entry

```typescript
{
  date: string,
  description: string,
  reference: string,
  debit: number,
  credit: number,
  running_balance: number
}
```

### Report (generic)

```typescript
{
  report_type: "trial-balance" | "income-statement" | "balance-sheet",
  date_from: string,         // YYYY-MM-DD
  date_to: string,           // YYYY-MM-DD
  rows: Array<{
    account_name: string,
    account_type: string,
    debit: number,
    credit: number,
    balance?: number          // computed net
  }>,
  totals: {
    total_debit: number,
    total_credit: number
  }
}
```
