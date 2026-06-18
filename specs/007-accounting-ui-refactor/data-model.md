# Data Model: Accounting UI Refactor

**Phase**: 1 — Design & Contracts
**Date**: 2026-06-18
**Feature**: Accounting UI Refactor (007)

> Frontend data shapes consumed and produced by the accounting UI components.
> Backend data model unchanged (defined in feature 005/006).

## Account

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | yes | Primary key |
| `name` | string | yes | Account display name |
| `type` | "Asset" / "Liability" / "Equity" / "Revenue" / "Expense" | yes | Account classification |
| `parent_id` | number / null | no | Parent account for hierarchy |
| `description` | string / null | no | Optional description |
| `is_active` | boolean | no | Soft-delete flag |
| `children` | Account[] | no | Nested child accounts (tree view) |
| `created_at` | string (ISO 8601) | no | Timestamp |
| `updated_at` | string (ISO 8601) | no | Timestamp |

**Validation rules**:
- `name` must be non-empty
- `type` must be one of the five valid values
- `parent_id` cannot create circular references (backend enforced)
- Hierarchy depth cannot exceed 10 levels (backend enforced)

## Journal Entry

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | no | Assigned on creation |
| `date` | string (YYYY-MM-DD) | yes | Transaction date |
| `description` | string | yes | Transaction narrative |
| `reference` | string | yes | Unique reference per tenant |
| `posted` | boolean | no | Locked after posting |
| `posted_at` | string (ISO 8601) / null | no | Set on post |
| `total_debit` | string (decimal) | no | Computed sum of line debits |
| `total_credit` | string (decimal) | no | Computed sum of line credits |
| `line_count` | number | no | Number of journal lines |
| `lines` | JournalEntryLine[] | yes | At least 2 lines required |
| `created_at` | string (ISO 8601) | no | Timestamp |

**Validation rules**:
- Must have at least 2 lines
- Total debits must equal total credits (within 0.001 tolerance)
- Lines cannot all be zero
- Reference must be unique per tenant
- Posted entries cannot be modified (backend enforced)

## Journal Entry Line

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | number | no | Assigned on creation |
| `account_id` | number | yes | FK to Account |
| `account_name` | string | no | Read-only, from backend |
| `account_type` | string | no | Read-only, from backend |
| `debit` | string (decimal) | no | Must be 0 if credit is set |
| `credit` | string (decimal) | no | Must be 0 if debit is set |
| `description` | string / null | no | Optional line description |

**Validation rules**:
- Cannot have both debit and credit non-zero
- Must have at least one of debit or credit non-zero
- Amounts must be non-negative

## Ledger

| Field | Type | Notes |
|---|---|---|
| `account` | LedgerAccountSummary | Account header info |
| `entries` | LedgerEntry[] | Sorted by date ascending |
| `totals` | LedgerTotals | Summary footer |

### LedgerAccountSummary

| Field | Type | Notes |
|---|---|---|
| `id` | string | Account ID as string |
| `name` | string | Account name |
| `type` | string | Account type |

### LedgerEntry

| Field | Type | Notes |
|---|---|---|
| `date` | string (YYYY-MM-DD) | Entry date |
| `description` | string | Entry description |
| `reference` | string | Entry reference |
| `debit` | string (decimal) | Line debit |
| `credit` | string (decimal) | Line credit |
| `running_balance` | string (decimal) | Cumulative balance |

### LedgerTotals

| Field | Type | Notes |
|---|---|---|
| `total_debit` | string (decimal) | Sum of all debits |
| `total_credit` | string (decimal) | Sum of all credits |
| `closing_balance` | string (decimal) | Net position |

## Reports

### Trial Balance

| Field | Type | Notes |
|---|---|---|
| `report_type` | "trial-balance" | Fixed |
| `date_from` | string / null | Filter range start |
| `date_to` | string / null | Filter range end |
| `rows` | ReportRow[] | Account rows |
| `totals` | ReportTotals | Grand totals |

### ReportRow

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | Account ID |
| `account_name` | string | Account name |
| `account_type` | string | Account type |
| `debit` | string (decimal) | Total debits |
| `credit` | string (decimal) | Total credits |

### ReportTotals

| Field | Type | Notes |
|---|---|---|
| `total_debit` | string (decimal) | Sum of all debits |
| `total_credit` | string (decimal) | Sum of all credits |

### Income Statement

| Field | Type | Notes |
|---|---|---|
| `report_type` | "income-statement" | Fixed |
| `date_from` | string / null | Filter range start |
| `date_to` | string / null | Filter range end |
| `revenues` | AccountBalance[] | Revenue accounts |
| `total_revenue` | string (decimal) | Sum of revenues |
| `expenses` | AccountBalance[] | Expense accounts |
| `total_expenses` | string (decimal) | Sum of expenses |
| `net_income` | string (decimal) | Revenue minus expenses |

### AccountBalance

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | Account ID |
| `account_name` | string | Account name |
| `balance` | string (decimal) | Net balance |

### Balance Sheet

| Field | Type | Notes |
|---|---|---|
| `report_type` | "balance-sheet" | Fixed |
| `as_of` | string / null | Snapshot date |
| `assets` | AccountBalance[] | Asset accounts |
| `total_assets` | string (decimal) | Sum of assets |
| `liabilities` | AccountBalance[] | Liability accounts |
| `total_liabilities` | string (decimal) | Sum of liabilities |
| `equity` | AccountBalance[] | Equity accounts |
| `total_equity` | string (decimal) | Sum of equity |
| `total_liabilities_and_equity` | string (decimal) | Liabilities + Equity |

## State Management

### `useAccounting` Hook State

```javascript
{
  accounts: Account[],       // Full accounts list
  loading: boolean,          // True during API calls
  error: Error | null        // Last error, null if no error
}
```

### Journal Entry Form State

```javascript
{
  date: '',                  // YYYY-MM-DD string
  description: '',           // Free text
  reference: '',             // Unique reference
  lines: [                   // At least 2 lines
    { account_id: null, debit: 0, credit: 0 }
  ],
  saving: false,             // True during submission
  fieldErrors: {}            // Server-side validation errors
}
```

### Report Selector State

```javascript
{
  type: 'trial-balance',     // Report type
  dateFrom: '',              // Date range start
  dateTo: '',                // Date range end
  asOf: ''                   // Balance sheet snapshot date
}
```
