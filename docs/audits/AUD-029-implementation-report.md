# AUD-029 — List Pagination + Kill the Invoice N+1 (Implementation Report)

- **Item**: AUD-029 (P3) — "List endpoints have no pagination (accounts, invoices,
  customers, stock movements, ledger), and `paid_amount`/`outstanding_balance` are
  computed live per row (N+1) on every invoice/payment list/retrieve."
- **Status**: **CLOSED**
- **Recommendation honored** (AUD-003 re-audit): "DRF pagination + annotate/cache
  `paid_amount`/`outstanding_balance` (kill N+1)."
- **Branch**: `014-auto-customer-code`
- **Date**: 2026-09-23
- **Constraint honored**: only AUD-029 was implemented. `services/api.js` behavior
  untouched; ledger/reports response contracts unchanged; no permission, tenant
  isolation, or auth change. Frontend lint stays at the locked baseline.

## 1. Summary

Every entity list endpoint now returns a standard DRF paginated envelope
(`count` / `next` / `previous` / `results`) at **25 rows/page** (client-adjustable
via `?page_size=` up to a 100 cap), and the invoice/payment "paid / outstanding"
money math is now **annotated in one GROUP BY** instead of firing
`PaymentService.invoice_paid_amount()` + `invoice_outstanding()` per row.

The N+1 source: every sales/purchase invoice row in a list triggered two service
queries (`invoice_paid_amount` then `invoice_outstanding` — the latter recomputing
the former), i.e. **2 queries × rows**. Payment lists compounded it:
`PaymentSerializer.get_invoice()` called the same two service methods per payment.
A 50-invoice list was 100+ extra queries.

## 2. Scope decisions (deliberate, documented)

| Endpoint | Paginated? | Why |
|---|---|---|
| Customers, Sales invoices, Sales payments | **yes** | tenant data, grows without bound |
| Vendors, Purchase invoices, Purchase payments | **yes** | same |
| Products, Warehouses, Stock balances, Stock movements, Stock adjustments | **yes** | same |
| Journal entries | **yes** | grows without bound |
| Team members, Pending invitations | **yes** | real `DefaultPagination` (was a manual `{count, results}` wrapper over an unbounded queryset) |
| **Accounts** (flat **and** tree) | **no** | bounded chart-of-accounts used as a searchable picker (`AccountSelect`, payment-form cash dropdown) and a tree; pagination would silently truncate the pickers and break the hierarchy. `pagination_class = None`. |
| Ledger | **no** | running balance is computed over the full history; paging would split the running balance across pages and corrupt it. |
| Reports | **no** | computed statement outputs (`@action` renderers), not row lists. |
| Settings singletons | **no** | no `list` action. |

Accounts was named in the audit text as a pagination target; it is the one
deliberate deviation, for the picker/tree reasons above.

## 3. What changed (backend)

New files:

- `backend/apps/core/pagination.py` — `DefaultPagination(PageNumberPagination)`:
  `page_size_query_param="page_size"`, `max_page_size=100`, page size from the
  `PAGE_SIZE` setting (25); opt-out lives per-viewset (`pagination_class = None`).
- `backend/apps/sales/tests/test_list_pagination_nplus1.py` — envelope + page_size
  + 100-row cap + N+1 query-count regression.
- `backend/apps/purchases/tests/test_list_pagination.py`
- `backend/apps/inventory/tests/test_products_pagination_search.py`
- `backend/apps/accounting/tests/test_journal_pagination.py`
- `backend/apps/accounts/tests/test_team_pagination.py` — team lists are real pages
  and honor `?page_size=`.

(12 tests across the five new files.)

Modified files:

- `backend/config/settings/base.py` — `REST_FRAMEWORK` gains
  `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE = 25`.
- `backend/apps/accounting/views.py` — `AccountViewSet.pagination_class = None`
  (bounded picker/tree, see §2).
- `backend/apps/sales/views.py` — invoice lists annotate
  `paid_amount = Coalesce(Sum("payments__amount", filter=Q(status=POSTED)), 0)`;
  payment lists annotate `_invoice_paid` via a **correlated Subquery** over the
  same tenant-scoped Payment table (`invoice_id` + POSTED). Deterministic ordering
  (`-created_at, -id`) on both.
- `backend/apps/purchases/views.py` — same pattern for purchase invoices
  (filter `direction=PAYABLE` + POSTED) and purchases payments
  (`purchase_invoice_id` + `direction=PAYABLE` + POSTED), same ordering tiebreaker.
- `backend/apps/inventory/views.py` — `StockAdjustmentViewSet` gets
  `-created_at, -id` ordering (stable pagination); `StockMovementViewSet` /
  `StockBalanceViewSet` get the same guarantee (`-created_at, -id` /
  `product__sku, id`); `ProductViewSet` gains a `search` query param
  (`sku`/`name` icontains) so the Products page search works under pagination.
- `backend/apps/accounts/views.py` — members + invitations GETs now use
  `DefaultPagination` (were hand-rolled `{"count": len(...), "results": [...]}`),
  with ordering (`user__email`, `-created_at, -id`).
- `backend/apps/accounting/views.py` — `JournalEntryViewSet` orders
  `-date, -id` (dates tie constantly; `-date` alone is not a stable page order).
- `backend/apps/sales/serializers.py` / `backend/apps/purchases/serializers.py` —
  `get_paid_amount` / `get_outstanding_balance` / `get_invoice` /
  `get_purchase_invoice` **prefer the annotation** and fall back to
  `PaymentService` only when it is absent (single-object retrieve/create/update
  paths).

### The N+1 fix, precisely

```python
paid_amount = Coalesce(
    Sum("payments__amount", filter=Q(payments__status=Payment.Status.POSTED)),
    Value(0, output_field=DecimalField(max_digits=19, decimal_places=4)),
)
```

`outstanding_balance` is computed in the serializer as
`max(obj.total - paid_amount, Decimal("0"))` — a Python-side subtraction on the
annotated value. The `output_field` is required: without it Django refuses to merge
the `DecimalField` SUM and the integer `Value(0)` ("Expression contains mixed
types"). `Greatest(...)` was deliberately **not** used for the max clamp because
SQLite stores DECIMAL as TEXT and would compare "9.99" > "10.00" lexicographically.

Payment lists annotate `_invoice_paid` once per row with a correlated subquery
(self-referential):

```python
invoice_paid = (
    Payment.objects.filter(
        invoice_id=OuterRef("invoice_id"),
        status=Payment.Status.POSTED,
    )
    .values("invoice_id")
    .annotate(total=Sum("amount"))
    .values("total")
)
```

Result: **1 GROUP BY query for the whole invoice page** (old code: 2 per row) and
**1 subquery for the whole payment page**. Query counts now flat in row count
(regression-guarded, see §6).

## 4. What changed (frontend)

- `frontend/src/lib/pagination.js` — `PAGE_SIZE = 25` shared constant.
- List pages read the envelope: `data.results` + `data.count`, keep `page`/`total`
  state, pass `?page=` in the fetch, and render the existing (previously unused)
  `components/ui/Pagination.jsx` under the table. CustomersPage, InvoicesPage,
  PaymentsPage, VendorsPage, PurchaseInvoicesPage, PurchasePaymentsPage,
  ProductsPage, StockPage (balances + movements, independent paging), AdjustmentsPage,
  JournalPage.
- Filter changes (status, date range, product search, movement type) reset to
  page 1 — reset happens in the `onChange` handler, so no effect-based setState
  and no new lint debt.
- After a delete/deactivate/refetch that empties the current (non-first) page, the
  fetch itself detects `results.length === 0 && page > 1` and re-requests page 1 —
  handled in the fetch callback (event/async context), keeping lint at baseline.
- Dropdown consumers that need the full catalog fetch `{ page_size: 100 }`. The
  fetches live in the **pages** (which already owned the fetch and pass the rows
  down as props — the forms themselves are unchanged): `InvoicesPage` customers,
  `PaymentsPage` posted invoices, `PurchaseInvoicesPage` vendors,
  `PurchasePaymentsPage` posted invoices, and `ProductSelect` (which fetches for
  itself). Accounts pickers are untouched because accounts are unpaginated
  (AccountSelect, PaymentForm/PurchasePaymentForm cash dropdowns, `useAccounting`).
- ProductsPage: the client-side `filtered` search was replaced by the new
  server-side `search` param (search over all pages, not just the loaded 25). The
  input is debounced 300 ms (timer in the `onChange` handler, cleared on unmount)
  so a keystroke does not fire a request.
- TeamPage: members/invitations already read `results`; now track `count` for the
  section subtotals, paginate the members table (with the same empty-page → page 1
  recovery as the other lists), and ask invitations for `page_size=100`.
- LedgerPage / ReportsPage / AccountsPage / Dashboard untouched (unpaginated or
  tree endpoints).
- `services/*.js` **unchanged** — all fetches already accepted a params object.

## 5. Config

Only `REST_FRAMEWORK` defaults changed (no per-endpoint config, no schema/migration):

```python
"DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
"PAGE_SIZE": 25,
```

`makemigrations --check --dry-run` → **No changes detected** (annotations and
settings only; no model change).

## 6. Verification

- Backend: **518 passed, 2 skipped** (506 prior + **12 new**; skips = 1 pre-existing
  + 1 opt-in Redis integration round-trip).
- Existing list-shape assertions updated to the envelope: sales (invoices, payments,
  customers, cross-tenant isolation), purchases (invoices, payments, vendors),
  inventory (products), accounting (journal entries, tenant isolation ×2,
  financial-integrity `posted` flag).
- Migrations clean (above).
- Frontend build: clean — **157 modules**, 443.78 kB JS / 123.61 kB gzip,
  11.67 kB CSS.
- Frontend lint: unchanged at the locked baseline — **13 problems (12 errors,
  1 warning)**, all pre-existing categories (11× `set-state-in-effect`,
  1× `exhaustive-deps`, 1× `no-undef` in `vite.config.js`); zero new debt, no
  rules weakened.

### New-test coverage map

| Concern | Test |
|---|---|
| Invoice envelope, `count`/`next`, `page_size=2` + `page=2` | `InvoiceListPaginationTests.test_invoice_list_is_paginated_envelope` |
| `page_size` capped at 100 (101 rows, `page_size=1000` → 100) | `...test_invoice_list_caps_page_size_at_100` |
| **N+1 guard**: query count flat 1 row → 5 rows | `...test_invoice_list_query_count_does_not_scale_with_rows` |
| Payment envelope + annotation still reports paid/outstanding | `PaymentListPaginationTests` |
| Purchase invoice / payment envelopes | `PurchaseInvoiceListPaginationTests`, `PurchasePaymentListPaginationTests` |
| Product envelope + server-side `search` | `ProductListPaginationSearchTests` |
| Journal entry envelope | `JournalEntryListPaginationTests` |
| Team members envelope; invitations honor `page_size` | `TeamListPaginationTests` |

## 7. Final review pass — defects found and fixed

A verification pass over the finished implementation found four AUD-029-introduced
defects; all four are fixed in the same commit.

1. **Non-deterministic page order.** Several newly paginated querysets ordered by
   a non-unique key: journal entries `-date` (dates tie constantly — the pagination
   test itself creates three entries on one date), stock balances `product__sku`
   (one row per warehouse), and the `-created_at` lists (ties possible in bulk
   creates). Under pagination that means rows can repeat or vanish across pages.
   Fixed with a unique tiebreaker on every paginated queryset (`-created_at, -id`,
   `-date, -id`, `product__sku, id`); `code`/`sku`/`name`-ordered lists are already
   unique per tenant by DB constraint.
2. **`?page_size=` silently ignored on the team endpoints.** The members/invitations
   views used a bare `PageNumberPagination` (`page_size_query_param = None`), so
   TeamPage's `page_size: 100` request for pending invitations returned 25 while
   the header showed the true `count`. Fixed by using the shared
   `DefaultPagination`; guarded by `TeamListPaginationTests`.
3. **One API request per keystroke.** Server-side product search moved filtering
   from memory to the API, so typing fired one request per character. Fixed with a
   300 ms debounce in the input handler (no effect-driven setState; lint unchanged).
4. **Team members could land on an empty last page.** TeamPage paginates members
   but lacked the empty-page → page 1 recovery the other 11 lists have, so removing
   the last member on the last page left an empty table. Fixed with the same
   recovery.

Not changed, deliberately: the client-side "next code/number" previews (§8) and the
100-row picker ceiling (§8) remain documented limitations, not defects — the server
mints the canonical reference at save, and the UI already reports a preview/save
mismatch.

## 8. Known limitations (documented, not defects)

- Dropdown consumers fetch a hard ceiling of 100 rows for their pickers (no
  paged/searchable combobox for them). Charts of accounts and typical per-tenant
  posted-invoice sets fit; a future picker with larger catalogs should move to a
  server-side-search combobox (same for the ProductSelect).
- The client-side "next number/code" previews on Invoices/Customers/Vendors pages
  now only see the loaded page; they remain best-effort previews only — the server
  mints the canonical reference at save (specs 013/014/015/016), so behavior is
  unchanged.

## 9. Files

See §3 backend + §4 frontend manifest. Scorecard: AUD-029 moved OPEN → CLOSED.