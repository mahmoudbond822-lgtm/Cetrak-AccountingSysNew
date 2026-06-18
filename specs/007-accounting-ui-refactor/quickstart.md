# Quickstart: Accounting UI Refactor

**Phase**: 1 — Design & Contracts
**Date**: 2026-06-18

> Validation scenarios to verify the refactored accounting UI works correctly.
> Prerequisites: Backend running with accounting endpoints, frontend dev server running.

## Prerequisites

1. Backend running on `http://localhost:8000`
2. Frontend dev server running on `http://localhost:5173`
3. User logged in as admin or accountant
4. Some accounts and journal entries already exist (created via feature 006)

## Scenario 1: Navigation & Layout

**Goal**: Verify all pages render with consistent layout.

1. Navigate to `/accounting/accounts`
2. Verify: Page renders with proper header, navigation sidebar, and content area
3. Click on "Journal" in navigation → `/accounting/journal`
4. Verify: Same layout, different content
5. Click on "Ledger" → `/accounting/ledger`
6. Verify: Same consistent layout
7. Click on "Reports" → `/accounting/reports`
8. Verify: Same consistent layout

**Expected**: All four pages share the same chrome (header, nav, footer). Navigation is smooth without full page reload.

## Scenario 2: Shared Components

**Goal**: Verify shared UI components render consistently.

1. Navigate to `/accounting/accounts`
2. Click "New Account"
3. Verify: Modal opens with proper title, input fields, and buttons
4. Verify: The Button component has consistent styling (background, padding, font)
5. Verify: The Input component has consistent styling (border, padding, font)
6. Close the modal
7. Navigate to `/accounting/journal`
8. Create a new entry
9. Verify: The same Button and Input styles appear in the journal form

**Expected**: All Button, Input, and Modal instances use the shared components with consistent styling.

## Scenario 3: Journal Entry Validation

**Goal**: Verify real-time balance detection and submission prevention.

1. Navigate to `/accounting/journal`
2. Click "New Entry"
3. Set date and reference
4. Add two lines:
   - Line 1: Select an account, set Debit = 1000
   - Line 2: Select an account, set Credit = 500
5. Verify: Balance indicator shows "Imbalanced" in red
6. Verify: Submit button is disabled
7. Change Line 2 credit to 1000
8. Verify: Balance indicator shows "Balanced" in green
9. Verify: Submit button becomes enabled

**Expected**: Balance updates within 200ms of input change. Imbalanced entries cannot be submitted.

## Scenario 4: Account Selection

**Goal**: Verify searchable account dropdown works.

1. Navigate to `/accounting/journal`
2. Click "New Entry"
3. Click on an account selector (first line)
4. Verify: Dropdown opens showing all accounts
5. Type a partial account name in the search box
6. Verify: List filters to matching accounts only
7. Select an account
8. Verify: Dropdown closes and account name is shown

**Expected**: Account selector is searchable and allows quick selection.

## Scenario 5: Create Journal Entry

**Goal**: Verify end-to-end journal entry creation.

1. Navigate to `/accounting/journal`
2. Click "New Entry"
3. Fill in: Date = today, Reference = "TEST-UI-001", Description = "UI Test Entry"
4. Add three lines:
   - Line 1: Select "Cash" account, Debit = 5000
   - Line 2: Select "Accounts Receivable" account, Debit = 3000
   - Line 3: Select "Revenue" account, Credit = 8000
5. Verify: Total Dr = 8000, Total Cr = 8000, indicator shows "Balanced"
6. Click "Submit"
7. Verify: Redirected to journal list page
8. Verify: New entry appears in the list with correct reference and totals

**Expected**: Entry is created and visible in the list. Balance validation passes.

## Scenario 6: Unsaved Changes Warning

**Goal**: Verify navigation away from unsaved form triggers warning.

1. Navigate to `/accounting/journal`
2. Click "New Entry"
3. Enter some data (do not submit)
4. Try to close the browser tab
5. Verify: A "Leave site?" confirmation dialog appears

**Expected**: User is warned about unsaved changes.

## Scenario 7: Ledger View

**Goal**: Verify ledger displays correct running balance.

1. Navigate to `/accounting/ledger`
2. Select an account that has journal entries
3. Verify: Account name and type displayed in header
4. Verify: Table shows Date, Reference, Description, Debit, Credit, Running Balance columns
5. Verify: Running balance increases/decreases correctly row by row
6. Verify: Totals row at bottom shows sum of debits, credits, and closing balance
7. Set a date range filter and click "Filter"
8. Verify: Results are filtered to the date range

**Expected**: Ledger displays accurate running balance and supports date filtering.

## Scenario 8: Report Generation

**Goal**: Verify all three report types render correctly.

1. Navigate to `/accounting/reports`
2. Select "Trial Balance" from report type dropdown
3. Set a date range covering existing entries
4. Click "Generate Report"
5. Verify: Report shows all accounts with debit and credit totals
6. Verify: Total debits equal total credits
7. Select "Income Statement"
8. Click "Generate Report"
9. Verify: Revenues and expenses sections are shown with net income
10. Select "Balance Sheet"
11. Set "As of" date
12. Click "Generate Report"
13. Verify: Assets = Liabilities + Equity

**Expected**: All three reports generate correctly with balanced totals.

## Cleanup

- Delete the test journal entry (if backend allows, or ignore for test data)
- Close the browser tab or navigate to a safe page
