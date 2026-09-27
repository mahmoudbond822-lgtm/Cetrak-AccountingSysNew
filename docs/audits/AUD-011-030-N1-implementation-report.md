# AUD-011 + AUD-030 + N1 Implementation Report

## 1. Objective

Close the three remaining precision/tenancy findings from the AUD-003 final
re-audit, in scope only:

- **AUD-011** — the four line tables had no `tenant_id` column (constitution §I
  gap); ownership existed only through the parent row.
- **AUD-030** — the database balance constraint and `JournalEntry.is_balanced`
  accepted any imbalance below `0.01`, so a genuinely out-of-balance entry could
  pass validation.
- **N1** — the frontend journal-entry form decided "balanced / imbalanced" with
  binary floating point and a `0.001` tolerance.

Explicitly out of scope and untouched: AUD-014, AUD-012, Dashboard v2, AI
features, deployment, currency/tax/inventory-accounting rules, and the
parent-based isolation that already worked.

## 2. Current-HEAD Verification

The repository was re-inspected before any edit; the historical `cc7e0b6`
baseline was not trusted.

- Branch `014-auto-customer-code`, starting HEAD `a9ca068`, working tree clean.
- `makemigrations --check --dry-run` before the change: "No changes detected".
- All four line models still inherited `BaseModel` (no tenant column).
- `JournalEntry.is_balanced` was `abs(total_debit - total_credit) < 0.01`, and
  `total_debit`/`total_credit` returned an `int` `0` for entries with no lines.
- `0002_balanced_entry_check.py` still created `check_entry_balanced()` with
  `ABS(SUM(debit) - SUM(credit)) < 0.01`.
- `JournalEntryForm.jsx:53` still used `Math.abs(totals.debit - totals.credit) < 0.001`
  to gate `canSubmit`.
- AUD-029 pagination, AUD-015 email, AUD-025 bcrypt and AUD-026 Celery were
  already committed and were left untouched.

Note on the historical report's wording: the `< 0.01` property the audit
attributed to `Account.is_balanced` (with a `models.py:67` citation) is on
`JournalEntry` in the current code — `Account` has no balance property. The
finding was real; only the model name in the citation was wrong.

## 3. Historical Findings

| Finding | Historical state | Current state at `a9ca068` | Still applicable | Required change |
|---|---|---|---|---|
| AUD-011 | Open (P2) | Four line tables still `BaseModel`-only | Yes | Add `tenant` FK, backfill from parent, NOT NULL, index, ORM integrity |
| AUD-030 | Open (P3) | `< 0.01` in model property and PG CHECK | Yes | Exact Decimal equality in both |
| N1 | Open (advisory P3) | `0.001` float tolerance gating submit | Yes | Integer minor-unit comparison |

## 4. AUD-011 — Tenant Column Alignment

### 4.1 Affected Tables

| Table | Model | Parent (source of truth) |
|---|---|---|
| `accounting_journalentryline` | `JournalEntryLine` | `JournalEntry.entry` → `JournalEntry.tenant` |
| `sales_invoiceline` | `SalesInvoiceLine` | `SalesInvoice.invoice` → `SalesInvoice.tenant` |
| `purchase_invoiceline` | `PurchaseInvoiceLine` | `PurchaseInvoice.invoice` → `PurchaseInvoice.tenant` |
| `inventory_stockadjustmentline` | `StockAdjustmentLine` | `StockAdjustment.adjustment` → `StockAdjustment.tenant` |

### 4.2 Model Changes

A new abstract base `apps.core.models.TenantOwnedLineModel` owns the shared
behaviour so the rule is defined once:

- `tenant = FK(core.Tenant, on_delete=CASCADE, related_name="+")`.
- `objects = TenantScopedQuerySet.as_manager()`, so lines now support
  `for_tenant()` like every other tenant-owned table.
- `parent_field` names the owning FK; `parent` resolves it.
- `save()` derives `tenant_id` from the parent when unset and **raises
  `ValidationError` when an explicit `tenant_id` disagrees with the parent**,
  so the column can never diverge from the authoritative parent.
- `clean()` applies the same check for `full_clean()` (forms/admin).

Each concrete line model now declares `parent_field` and inherits the base.
`JournalEntryLine.clean()` was amended to call `super().clean()` so the
tenant check is not shadowed by its debit/credit rules.

No serializer exposes `tenant`: all four line serializers declare explicit
`fields` lists, so the new column is not part of any API contract.

### 4.3 Migration

One migration per app, each in three deterministic steps:

1. `AddField` with `null=True` (no default, so no historical row is assigned a
   placeholder tenant).
2. `RunPython` backfill from the parent tenant.
3. `AlterField` to `null=False` (NOT NULL), then `AddIndex`.

| Migration | Steps |
|---|---|
| `accounting/0004_journalentryline_tenant_and_more.py` | AddField → backfill → NOT NULL → index |
| `sales/0005_salesinvoiceline_tenant_and_more.py` | AddField → backfill → NOT NULL → index |
| `purchases/0003_purchaseinvoiceline_tenant_and_more.py` | AddField → backfill → NOT NULL → index |
| `inventory/0002_stockadjustmentline_tenant_and_more.py` | AddField → backfill → NOT NULL → index |

All four are reversible (`RunPython(backfill, noop)` plus Django's generated
`RemoveField`), and none is destructive: no row is deleted, no default is
applied to history, and `atomic` behaviour is Django's default per operation.

### 4.4 Backfill

The backfill is a correlated subquery against the authoritative parent, not a
join-rewrite and not a blanket default:

```python
Line.objects.filter(tenant_id__isnull=True).update(
    tenant_id=Subquery(Parent.objects.filter(pk=OuterRef("<parent>_id")).values("tenant_id")[:1])
)
```

Each migration then re-counts NULL rows and raises `RuntimeError` with the
count if any line could not be resolved, so a partial backfill can never be
mistaken for success. The migration test proves all four tables round-trip:
each migration is reverted, a legacy row is inserted with the pre-migration
column set (no tenant column), the migration is re-applied, and the row returns
with the parent's tenant and zero NULLs remaining.

`F("<parent>__tenant_id")` was tried first and rejected: Django forbids joined
field references in `QuerySet.update()` (`FieldError`), so the `Subquery` form
is used.

### 4.5 Indexes

Composite `(tenant, <parent>)` per table, matching the existing convention on
`StockMovement` (`Index(fields=["tenant", "purchase_invoice"])`):

- `acct_line_tenant_entry_idx`
- `sales_line_tenant_invoice_idx`
- `purch_line_tenant_invoice_idx`
- `inv_line_tenant_adj_idx`

The parent FK keeps its own implicit index, so `filter(tenant=…, entry=…)` and
tenant-wide line reads are both covered.

### 4.6 Tenant Integrity

- ORM: the parent is the single source of truth; a divergent `tenant_id` raises
  on `save()` and on `full_clean()`.
- Database: `NOT NULL` on the column. A raw `bulk_create()` that bypasses
  `save()` and omits the tenant fails with `IntegrityError` (asserted by test),
  which also protects future `bulk_create` call sites.
- Deliberately **not** added: a PostgreSQL trigger that cross-checks
  `line.tenant_id` against the parent on every write. It would duplicate the ORM
  rule in a second language, cannot be exercised by the SQLite test database, and
  the existing parent-scoped API already prevents cross-tenant attachment. This
  is recorded as a limitation, not silently omitted.

### 4.7 Security

- No new API surface: `tenant` is not in any line serializer, so a client cannot
  submit or read it.
- No service changes were needed: every production line creation
  (`JournalEntryService.create_entry`, invoice/adjustment services, posting
  paths) passes the tenant-scoped parent object, so the derived tenant is
  always the current tenant's.
- `for_tenant()` on the line manager enables the same scoping style used
  everywhere else; cross-tenant read/write/delete of lines was already blocked
  by parent-scoped services and permission checks, and those tests remain green.

## 5. AUD-030 — Decimal-Exact Balance Enforcement

### 5.1 Database Constraint

`accounting/0005_decimal_exact_balance_check.py` replaces
`check_entry_balanced(UUID)` with exact equality and re-installs the
`balanced_entry_check` constraint:

```sql
COALESCE((SELECT SUM(debit)  FROM … ), 0) = COALESCE((SELECT SUM(credit) FROM … ), 0)
```

- `debit`/`credit` are `NUMERIC(19,4)`, so PostgreSQL `SUM` and `=` are exact
  decimal operations — no float, no tolerance, no rounding.
- Before touching the constraint the migration counts existing entries that are
  not exactly balanced and **aborts with a clear error** if any are found
  (non-destructive: nothing is modified, and no accounting data is silently
  rewritten).
- The reverse operation restores the previous tolerant function, so the change
  is reversible.
- The migration remains a no-op on non-PostgreSQL vendors, as the original did.

### 5.2 Account.is_balanced

`JournalEntry.is_balanced` is now `self.total_debit == self.total_credit` —
exact Decimal equality at field precision, no float literal. `total_debit` and
`total_credit` return `Decimal("0")` instead of the int `0` for entries without
lines, so the property is Decimal-typed end to end. The property lives on
`JournalEntry`, not `Account` (see §2); `Account` has no balance property and
none was invented.

No tolerance remains anywhere in production code: a scan of `apps/` and
`config/` (excluding tests and migrations) finds no `0.01`, no `abs(`, no
`float(`, and no `round(` in accounting code.

### 5.3 Posting Paths

Audited, not rewritten — every path was already Decimal-exact and stays that way:

| Path | Balance logic | Change |
|---|---|---|
| `JournalEntrySerializer.validate` | `Decimal(str(...))` sums, `!=` rejection | none (already exact) |
| `JournalEntryService.post_entry` | `Decimal` sums, `!=` → `ValueError` | none (already exact) |
| `JournalEntry.clean()` / `full_clean()` | now exact via `is_balanced` | tolerance removed |
| `sales/services.py` invoice + payment posting | `_quantize(..., ROUND_HALF_UP)` on both sides, symmetric legs | none |
| `purchases/services.py` AP posting | shares `_quantize`, symmetric legs | none |
| `inventory/services.py` adjustment + movement posting | `_quantize`, symmetric legs | none |
| Reversal / adjustment paths | reuse the above services | none |

The only functional change is that the model-level check no longer tolerates a
sub-cent imbalance, which aligns it with the serializer, the posting service,
and the new database constraint.

### 5.4 Decimal Precision

Precision is unchanged everywhere: `NUMERIC(19,4)` money fields,
`DecimalField(max_digits=19, decimal_places=4)`, `Decimal("0.00")` rates,
`ROUND_HALF_UP` quantization for proportional discount allocation. No rounding
was introduced, and no tolerance can hide an imbalance.

## 6. N1 — Frontend Precision Hygiene

`frontend/src/components/accounting/journal/JournalEntryForm.jsx` decided
"balanced" with `Math.abs(debit - credit) < 0.001` over `parseFloat` sums, and
that decision gated **Save Draft** (`canSubmit`). Float addition can drift, and
`0.001` is a tolerance that hides a real imbalance — the backend (which decides
correctness) uses exact equality at 4 decimal places.

Change (smallest correct fix, no new dependency):

- Money is converted to integer minor units at the backend precision
  (`MONEY_UNITS = 10000`, matching `NUMERIC(19,4)`) and summed as integers.
- `balanced` is now `totals.debit === totals.credit` — exact integer equality.
- The balance bar and the save payload are rendered/derived from the same units
  (`fromMoneyUnits`), so display and payload agree with the gate and the payload
  is quantized to 4 dp like the backend columns.

Remaining limitations, deliberately not changed:

- `parseFloat(...).toFixed(2)` in `LedgerTable`, `ReportTable`, `JournalPage`
  and `JournalLineRow` is display/formatting only and is not an accounting
  decision; converting it to a decimal library is out of scope.
- `InvoiceForm`/`PurchaseInvoiceForm` `parseFloat` helpers compute on-screen
  previews; the backend recomputes and stores every line total, so they are not
  an invariant either.
- Browser float parsing is still used to read the user's typed value before it
  is quantized; a decimal library would be needed for input parsing itself, and
  the server remains authoritative.

## 7. Tests

20 new tests, all passing:

| File | Tests | Covers |
|---|---|---|
| `apps/core/tests/test_tenant_line_integrity.py` | 7 (12 subtests) | tenant inherited from parent for all four tables; explicit matching tenant kept; divergent tenant rejected on `save()` and `full_clean()`; `for_tenant()` scoping; `NOT NULL` proven by `bulk_create()` → `IntegrityError`; no cross-tenant visibility |
| `apps/core/tests/test_line_tenant_backfill_migration.py` | 1 (4 subtests) | migration round-trip for all four tables: legacy row inserted pre-migration, backfilled to the parent tenant, zero NULLs left |
| `apps/accounting/tests/test_decimal_exact_balance.py` | 9 | exact match balanced; 0.01 / 0.005 / 0.0001 imbalances all unbalanced; totals are `Decimal`; `full_clean()` rejects 0.005; `post_entry` rejects 0.005 and leaves the entry unposted; API returns 400 and writes nothing |
| `apps/accounting/tests/test_decimal_exact_balance_constraint.py` | 3 | shipped PG SQL uses `=` with no `ABS(`/`0.01`; the precheck query detects non-zero imbalance; the reverse function restores the tolerant version deliberately |

No existing test was modified, relaxed, or skipped. The pre-existing
`is_balanced` assertions in the inventory and purchasing suites still hold, now
under a stricter rule.

## 8. Regression Results

| Gate | Result |
|---|---|
| New AUD-011/AUD-030/N1 tests | 20 passed, 0 failed, 0 skipped |
| Affected apps (accounting, core, sales, purchases, inventory) | 429 passed, 2 skipped, 16 subtests |
| Full backend suite | **538 passed, 2 skipped, 16 subtests** (518 before this work + 20 new) |
| Skips | 1 pre-existing + 1 opt-in `CETRAK_CELERY_INTEGRATION` Redis round-trip — unchanged, no new skip |
| Frontend build | clean; 157 modules, 443.84 kB JS / 123.64 kB gzip, 11.67 kB CSS |
| Frontend lint | 13 problems (12 errors, 1 warning) — locked baseline, zero new |

Authentication, tenant isolation, accounting, sales, purchasing/AP, inventory,
payments, Celery, email and pagination suites were all exercised by the full
run; no behaviour outside the balance gate and the line ownership rule changed.

## 9. Migration Verification

- `makemigrations --check --dry-run` before: "No changes detected"; after:
  "No changes detected" (models and migrations agree).
- `migrate --plan` lists exactly the five new migrations in dependency order:
  `accounting.0004`, `accounting.0005`, `inventory.0002`, `purchases.0003`,
  `sales.0005`.
- Every migration was inspected manually: no `DeleteModel`/`AlterField` on
  monetary columns, no `default=` on the new column, no data deletion, the
  backfill precedes the `NOT NULL` tightening, and the index is added last.
- The four backfills were executed for real by the round-trip test against the
  test database, including the NULL-orphan guard.
- The PostgreSQL CHECK-constraint migration is a documented no-op on SQLite; its
  SQL is pinned by `test_decimal_exact_balance_constraint.py` and its
  offender-count guard is therefore unexercised locally. Verifying it against a
  live PostgreSQL instance is the one outstanding verification step (§12).

## 10. Files Changed

Backend models / core:

- `backend/apps/core/models.py` — new `TenantOwnedLineModel`.
- `backend/apps/accounting/models.py` — `JournalEntryLine` inherits it, index,
  exact `is_balanced`, `Decimal` totals, `clean()` chain.
- `backend/apps/sales/models.py` — `SalesInvoiceLine` inherits it, index.
- `backend/apps/purchases/models.py` — `PurchaseInvoiceLine` inherits it, index.
- `backend/apps/inventory/models.py` — `StockAdjustmentLine` inherits it, index.

Migrations:

- `backend/apps/accounting/migrations/0004_journalentryline_tenant_and_more.py`
- `backend/apps/accounting/migrations/0005_decimal_exact_balance_check.py`
- `backend/apps/sales/migrations/0005_salesinvoiceline_tenant_and_more.py`
- `backend/apps/purchases/migrations/0003_purchaseinvoiceline_tenant_and_more.py`
- `backend/apps/inventory/migrations/0002_stockadjustmentline_tenant_and_more.py`

Tests:

- `backend/apps/core/tests/test_tenant_line_integrity.py`
- `backend/apps/core/tests/test_line_tenant_backfill_migration.py`
- `backend/apps/accounting/tests/test_decimal_exact_balance.py`
- `backend/apps/accounting/tests/test_decimal_exact_balance_constraint.py`

Frontend:

- `frontend/src/components/accounting/journal/JournalEntryForm.jsx`

Documentation:

- `docs/audits/AUD-011-030-N1-implementation-report.md` (this file)

## 11. Security Review

| Check | Result |
|---|---|
| Cross-tenant read of a line | Blocked — `for_tenant()` scoping plus parent-scoped services; asserted in tests |
| Cross-tenant write (line on another tenant's parent) | Blocked — `save()` raises `ValidationError`; API paths never reach it because parents are tenant-scoped |
| Cross-tenant delete | Unchanged and still parent-scoped; no new delete path was added |
| Client-assignable tenant | Not possible — `tenant` is absent from every line serializer and rejected when divergent |
| Parent/line divergence | Impossible by construction: the parent is the source of truth and a divergent value is refused on save and on `full_clean()` |
| Float-based accounting invariant | None left in scope: no `0.01`, `abs(`, `float(`, `round(` in production accounting code; frontend gate is integer minor units |
| Tolerance hiding an imbalance | Removed at all three layers (model, serializer/posting already exact, database CHECK); a 0.005 imbalance is now rejected everywhere |
| Rounding silently balancing an entry | Not possible — quantization is unchanged and symmetric; the new CHECK requires exact equality |
| Secrets / debug code | None added; no credentials, tokens, or scratch scripts in the diff |

## 12. Remaining Limitations

1. The PostgreSQL CHECK constraint and its offender-count guard are not executed
   by the local SQLite test database. Before production rollout, run
   `migrate` against a PostgreSQL instance seeded with representative data
   (this also exercises `0002` → `0005`). If legacy entries exist that are
   out of balance by less than a cent, the migration aborts by design and they
   must be remediated first.
2. Cross-table parent/child tenant equality is enforced in the ORM, not by a
   database trigger. A direct SQL write could still pair a line with a foreign
   tenant's parent, though nothing in the application can do it and
   `NOT NULL` still blocks the common mistake.
3. `0002_balanced_entry_check.py` is intentionally left unchanged (historical
   record); it is superseded at runtime by `0005`. Its tolerant function is also
   preserved as the reverse target of `0005`.
4. Frontend money reading still goes through `parseFloat` before quantization
   (display, ledger, reports). That is presentation-only; removing it entirely
   would need a decimal library and a broader frontend refactor, out of scope.
5. `Account` has no balance property; the N1 backend item concerned
   `JournalEntry.is_balanced` and is closed there. The residual float literal
   the audit also mentioned (`Account.is_balanced`) does not exist in the current
   codebase — verified, not deferred.

## 13. Commit

```text
Commit: feat(tenancy): align tenant columns and decimal balance enforcement
```

One focused commit containing only AUD-011, AUD-030, N1, their migrations, their
tests, and this report. Not pushed, not deployed.

## 14. Final Status

- **AUD-011: CLOSED** — all four line tables carry a NOT NULL `tenant_id`
  backfilled from the authoritative parent, indexed, with ORM-level divergence
  rejection, a proven backfill migration per app, and cross-tenant regression
  tests.
- **AUD-030: CLOSED** — `JournalEntry.is_balanced` and the PostgreSQL
  `balanced_entry_check` are both exact Decimal equality with no tolerance; the
  migration aborts rather than silently accepting legacy imbalances. Caveat: the
  PG path needs one live-PostgreSQL migration run before rollout (§12.1).
- **N1: CLOSED** — the client balance gate no longer uses binary floats or a
  `0.001` tolerance; it compares integer minor units at the backend precision.
  Display-only float formatting remains and is documented as out of scope.
