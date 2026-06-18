# Quickstart: Accounting Frontend

## Prerequisites

- Backend running at `http://localhost:8000` (or `backend:8000` in Docker)
- Frontend dev server at `http://localhost:5173`
- Seeded accounting data (accounts + journal entries)
- Authenticated user with Admin/Accountant role in a tenant

## Setup

```bash
# Backend — apply migrations
cd backend
py manage.py migrate

# Backend — seed test data (if available)
py manage.py seed_accounting

# Frontend — start dev server
cd frontend
npm run dev
```

## Validation Scenarios

### Scenario 1: Chart of Accounts

1. Login and navigate to `/accounting/accounts`
2. **Expected**: A tree view of accounts grouped by type, with expand/collapse on parent nodes
3. Click "Create Account" — fill name "Test Asset", type "Asset", save
4. **Expected**: New account appears in the tree under Assets
5. Click edit on the account, change name to "Test Asset (edited)", save
6. **Expected**: Account name updates in the tree

### Scenario 2: Journal Entry Creation

1. Navigate to `/accounting/journal/new`
2. Fill date (today), description "Test entry", reference "TEST-001"
3. Add line 1: select "Cash" account, debit "1000"
4. Add line 2: select "Owner's Equity" account, credit "1000"
5. **Expected**: Balance indicator shows "Balanced: 1000 = 1000"
6. Click "Post"
7. **Expected**: Redirect to journal entries list, entry appears with locked status

### Scenario 3: Imbalance Rejection

1. Navigate to `/accounting/journal/new`
2. Add line 1: debit "100", line 2: credit "50"
3. **Expected**: Error message "Total debit must equal total credit"
4. **Expected**: "Post" button is disabled

### Scenario 4: Ledger View

1. Navigate to `/accounting/ledger/{account-id}` for an account with transactions
2. **Expected**: Table with columns: Date, Description, Debit, Credit, Running Balance
3. Apply date range filter
4. **Expected**: Only entries within the date range shown

### Scenario 5: Trial Balance Report

1. Navigate to `/accounting/reports`
2. Select "Trial Balance" type, set date range
3. **Expected**: Report shows all accounts with debit/credit balances
4. **Expected**: Total debits equals total credits

### Scenario 6: Income Statement

1. Navigate to `/accounting/reports`
2. Select "Income Statement"
3. **Expected**: Shows revenue and expense accounts, net income calculated

### Scenario 7: Balance Sheet

1. Navigate to `/accounting/reports`
2. Select "Balance Sheet"
3. **Expected**: Shows assets = liabilities + equity

## API Endpoints Used

| Method | URL | Source |
|--------|-----|--------|
| GET | `/api/v1/accounting/accounts/` | Existing |
| POST | `/api/v1/accounting/accounts/` | Existing |
| PATCH | `/api/v1/accounting/accounts/{id}/` | Existing |
| GET | `/api/v1/accounting/accounts/{id}/` | Existing |
| GET | `/api/v1/accounting/journal-entries/` | Needs routing activation |
| POST | `/api/v1/accounting/journal-entries/` | Needs routing activation |
| GET | `/api/v1/accounting/journal-entries/{id}/` | Needs routing activation |
| GET | `/api/v1/accounting/ledger/` | Needs implementation |
| GET | `/api/v1/accounting/reports/trial-balance/` | Needs implementation |
| GET | `/api/v1/accounting/reports/income-statement/` | Needs implementation |
| GET | `/api/v1/accounting/reports/balance-sheet/` | Needs implementation |
