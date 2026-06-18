# API Contracts: Accounting UI

**Phase**: 1 — Design & Contracts
**Date**: 2026-06-18

> Frontend service layer interface for the accounting API.
> Backend endpoints defined in feature 005/006.

## Service Layer Interface (`accountingService.js`)

### Accounts

```javascript
// List all active accounts
// GET /api/v1/accounting/accounts/
accountingService.getAccounts()
// Returns: Account[]
// Query params: ?type=Asset (optional filter), ?tree=true (optional tree mode)

// Create a new account
// POST /api/v1/accounting/accounts/
accountingService.createAccount({ name, type, parent_id?, description? })
// Returns: Account
// Body: { name: string, type: string, parent_id?: number, description?: string }
// Errors: 400 (validation), 403 (permission denied)

// Update an account
// PATCH /api/v1/accounting/accounts/{id}/
accountingService.updateAccount(id, { name?, type?, description? })
// Returns: Account
// Errors: 400 (validation, e.g., type change on used account), 404, 405 (cannot deactivate used account)

// Deactivate an account
// DELETE /api/v1/accounting/accounts/{id}/
accountingService.deleteAccount(id)
// Returns: 204 No Content
// Errors: 400 (has active children or journal lines), 404
```

### Journal Entries

```javascript
// List journal entries
// GET /api/v1/accounting/journal-entries/
accountingService.getJournalEntries({ date_from?, date_to? })
// Returns: JournalEntry[] (with lines, totals, line_count)

// Create a journal entry
// POST /api/v1/accounting/journal-entries/
accountingService.createJournalEntry({ date, description, reference, lines })
// Body: { date: string, description: string, reference: string, lines: [{ account_id, debit, credit }] }
// Returns: JournalEntry
// Errors: 400 (validation: imbalanced, <2 lines, bad account), 403

// Post (lock) a journal entry
// POST /api/v1/accounting/journal-entries/{id}/post/
accountingService.postJournalEntry(id)
// Returns: { id, posted: true, posted_at, reference, date }
// Errors: 400 (already posted, imbalanced, no lines), 404
```

### Ledger

```javascript
// Get ledger for a specific account
// GET /api/v1/accounting/ledger/?account_id={id}&date_from=&date_to=
accountingService.getLedger(accountId, { date_from?, date_to? })
// Returns: Ledger
// Errors: 400 (missing account_id), 404 (account not found)
```

### Reports

```javascript
// Trial Balance
// GET /api/v1/accounting/reports/trial-balance/?date_from=&date_to=
accountingService.getTrialBalance({ date_from?, date_to? })
// Returns: TrialBalance

// Income Statement
// GET /api/v1/accounting/reports/income-statement/?date_from=&date_to=
accountingService.getIncomeStatement({ date_from?, date_to? })
// Returns: IncomeStatement

// Balance Sheet
// GET /api/v1/accounting/reports/balance-sheet/?as_of=
accountingService.getBalanceSheet({ as_of? })
// Returns: BalanceSheet
```

## Error Response Format

All API errors follow:

```javascript
{
  detail?: string,                    // Generic error
  non_field_errors?: string[],        // Validation errors not tied to a field
  <field_name>?: string | string[]    // Per-field validation errors
}
```

HTTP Status Codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Validation error |
| 403 | Permission denied |
| 404 | Not found |
| 405 | Method not allowed (immutable entries) |
