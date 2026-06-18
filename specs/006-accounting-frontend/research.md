# Research: Accounting Frontend

## U1: JournalEntryViewSet Routing

**Decision**: Add `JournalEntryViewSet` to `urls.py`

The viewset is fully implemented in `views.py` with list/create/retrieve and 405 overrides for update/delete. The only missing piece is URL registration.

**Rationale**: Minimal change — add import + one router.register line.

**Implementation**:
```python
# backend/apps/accounting/urls.py
from apps.accounting.views import AccountViewSet, JournalEntryViewSet

router.register(r"journal-entries", JournalEntryViewSet, basename="journalentry")
```

## U2: Report Aggregation Queries

**Decision**: Implement three reports via a new `ReportService` using Django ORM aggregation

**Trial Balance** — Group `JournalEntryLine` by `account_id`, sum debit and credit for all posted entries within a date range. Include account name and type.

**Income Statement** — Filter accounts of type Revenue and Expense. Group by account, sum net balance (credit - debit for revenue, debit - credit for expense). Compute net income as total revenue - total expense.

**Balance Sheet** — Filter accounts of type Asset, Liability, Equity. For each account, compute net balance (total debits - total credits). Use unbounded date range (or up to given date).

**Rationale**: ORM aggregation queries are efficient and the data volume at small-business scale is low (<100k journal lines). No need for materialized views or cached aggregates for MVP.

## U3: Ledger Running Balance

**Decision**: Compute running balance in Python after fetching sorted lines

**Implementation**: Query `JournalEntryLine` for a given account, ordered by `entry__date`, `created_at`. Iterate and compute cumulative balance (initial zero, debit adds, credit subtracts).

**Rationale**: Running balance is a window function problem. PostgreSQL supports `SUM(...) OVER (ORDER BY ...)`, but using Python iteration is simpler for MVP and fine for typical account volumes (<10k lines per account). Can be optimized with a DB window function later if performance becomes an issue.

## U4: Report Permissions

**Decision**: Reports need `Manager` role access per the spec. The existing `HasAccountingAccess` grants `Admin` or `Accountant`. For MVP, extend `HasAccountingAccess` to also allow `Manager`, OR create a separate `CanViewReports` permission.

**Decision**: Use a separate permission class `CanViewReports` that allows `Admin`, `Accountant`, and `Manager`, since the spec differentiates report access from journal/account access.

## Existing Frontend Patterns Summary

| Aspect | Pattern |
|--------|---------|
| Styling | Inline `style` props + CSS variables from `index.css` |
| Routing | `BrowserRouter` + `Routes` + `Route` in `App.jsx`, `ProtectedRoute` wrapper |
| API calls | Axios instance from `services/api.js`, auto JWT + tenant headers |
| Forms | Controlled `useState` with single object + `handleChange` by `e.target.name` |
| State | Component-local `useState` + `localStorage` for auth via helpers |
| Error handling | `try/catch`, `err.response?.data.detail` or object flattening |
| No libraries | No UI library, no state management, no form library |
