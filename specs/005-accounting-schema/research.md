# Research: Accounting Schema

**Phase**: 0 — Technology & Approach Decisions

**Date**: 2026-06-18

## Unknown 1: Chart of Accounts Tree Implementation

**Question**: How to model and query the hierarchical (parent-child) account structure in Django 6.0.4?

### Decision: Materialized path via `parent_id` FK + recursive CTE

Use a simple self-referencing foreign key (`parent = ForeignKey("self")`) and PostgreSQL's recursive CTE (`WITH RECURSIVE`) for tree queries. No third-party library.

### Rationale

- **django-mptt**: Uses modified pre-order tree traversal (MPTT). Requires writes to rebalance siblings on every insert — unnecessary complexity for a chart of accounts where the tree is modified infrequently (accountants add accounts, but rarely reorder them). django-mptt also has known compatibility issues with Django 6.0 (the project last released a version compatible with Django 5.x).
- **django-treebeard**: Supports multiple tree algorithms (MPTT, adjacency list, materialized path). Well-maintained but adds a dependency for a feature that PostgreSQL handles natively. The adjacency list mode overlaps with a plain `parent_id` FK.
- **Materialized path + recursive CTE**: Django's `parent_id` FK is the standard adjacency list model. PostgreSQL's `WITH RECURSIVE` fetches entire subtrees in a single query. For the spec's target scale (500 accounts max), this performs well with an index on `parent_id`. No extra dependencies, no write-time overhead.

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| django-mptt | Mature, built-in tree utilities | Write-heavy rebalancing; Django 6 compatibility uncertain |
| django-treebeard | Multiple algos, well-maintained | Unnecessary dependency for 500-account scale |
| Pure parent FK + Python recursion | Simple model | N+1 queries for deep trees; acceptable only at small scale |
| **Parent FK + recursive CTE** | Single query, no deps, indexed | Requires raw SQL or `django-cte` helper |

### Implementation Note

Use Django's `queryset.raw()` or the `django-cte` library (lightweight, pure-SQL CTE helper) for the recursive tree query. The `parent_id` FK gets `db_index=True`.

---

## Unknown 2: Balanced-Entry Enforcement Strategy

**Question**: How to enforce the constitutional hard rule (FR-006) — total debits must equal total credits for every journal entry — at both the application and data layers?

### Decision: Application-level validation in `services.py` + database CHECK constraint

Apply validation in two layers:

1. **Application layer**: Django model `clean()` method and `ModelSerializer.validate()` reject unbalanced entries before they reach the database. The service layer (`JournalEntryService.create_entry`) is the single entry point and always calls `full_clean()`.
2. **Data layer**: A database CHECK constraint on the `JournalEntry` table, enforced via `ALTER TABLE ... ADD CONSTRAINT ... CHECK (...)`. The constraint uses a PostgreSQL function or a direct query pattern: `(SELECT COALESCE(SUM(debit), 0) FROM journal_entry_line WHERE entry_id = id) = (SELECT COALESCE(SUM(credit), 0) FROM journal_entry_line WHERE entry_id = id)`.

### Rationale

- Django's `clean()` is sufficient for normal API usage (95%+ of cases) and provides user-friendly error messages.
- The CHECK constraint is the constitutional safeguard — it catches direct SQL inserts, bulk imports, migrations, and any future code path that bypasses the service layer.
- Combining both layers satisfies FR-006 ("enforced at both the application layer and the data layer").

### Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| Django `clean()` only | Simple, standard pattern | Bypassed by direct DB access, `QuerySet.update()`, raw SQL |
| DB trigger (BEFORE INSERT/UPDATE) | Catches all mutations | More complex; harder to maintain and test |
| DB CHECK constraint | Declarative, indexed, no maintenance | Cannot reference another table directly — must use PostgreSQL function or `EXCLUDE` |
| **Django clean() + DB CHECK** | Two-layer; app provides good errors, DB provides hard stop | CHECK constraint requires a PostgreSQL function for cross-table validation |

### Implementation Note

For the CHECK constraint on `JournalEntry`, create a PostgreSQL function:

```sql
CREATE FUNCTION check_entry_balanced(entry_uuid UUID) RETURNS BOOLEAN AS $$
    SELECT ABS(COALESCE((SELECT SUM(debit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0) -
               COALESCE((SELECT SUM(credit) FROM accounting_journalentryline WHERE entry_id = entry_uuid), 0)) < 0.01;
$$ LANGUAGE SQL IMMUTABLE;

ALTER TABLE accounting_journalentry
ADD CONSTRAINT balanced_entry_check CHECK (check_entry_balanced(id));
```

The tolerance (`< 0.01`) handles floating-point rounding in multi-line entries with fractional amounts. This is a standard accounting practice (1-cent tolerance).
