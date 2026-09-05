# Research: Sales Cycle (Foundation)

**Purpose**: Record the technical decisions behind the Feature 009 design before implementation. Built from inspection of the existing repository.

## 1. Existing Architecture Constraints

- **Tenant isolation** is enforced by `TenantResolutionMiddleware` (`apps/core/middleware.py`), which sets `request.tenant_id` from the JWT `tenant_id` claim or the `X-Tenant-ID` header and returns 403 when the user has no membership. All tenant-scoped models use `TenantScopedQuerySet.for_tenant()`.
- **Business logic lives in services** (`apps/accounting/services.py`) per Constitution Article IV; viewsets (`apps/accounting/views.py`) delegate to services instead of containing logic.
- **Money** uses `DecimalField(max_digits=19, decimal_places=4)` across the accounting module. Balance checks exist in serializers (`JournalEntrySerializer.validate`), services (`JournalEntryService.post_entry`), and a PostgreSQL CHECK constraint (`0002_balanced_entry_check`).
- **Journal entries are immutable** after creation at the API level (`JournalEntryViewSet` returns 405 for update/delete), posted via a `@action(detail=True, url_path="post")` (`JournalEntryViewSet.post`), and `reference` is user-supplied and enforced unique per tenant.
- **Permissions** are thin `BasePermission` classes: `HasAccountingAccess` (Admin+Accountant), `CanViewReports` (Admin+Accountant+Manager), `IsAdminUser` (Admin).
- **Feature 008** established the isolation pattern in `apps/accounting/serializers.py`: `AccountSerializer.validate_parent_id` uses `models.Account.objects.for_tenant(request.tenant_id).get(pk=...)`, and `TenantScopedAccountField` replaces the queryset at serialization time. This pattern is reused for every sales FK.
- **`apps.sales` already exists** in `INSTALLED_APPS` (`config/settings/base.py`) with only an `__init__.py` — no settings change is needed.
- **Frontend** centralizes API calls in `services/accountingService.js` (axios), reuses CSS-variable styling (`--accent`, `--border`, `--bg`, `--text`), uses `AccountingNav` for the accounting section, and gates actions by `activeTenantRole` from `localStorage`. There is **no frontend test framework** installed; verification is `npm run build` + `npm run lint`.

## 2. Scope: Which Sales Documents in This Feature?

**Decision: Customers + Sales Invoices. Quote and Order are deferred.**

Rationale:

- The Definition of Done requires customer management, invoice workflow, and accounting integration. Quote/Order are not required by it.
- The highest-value, highest-risk capstone is invoice posting → balanced journal entry. Delivering that end-to-end early maximizes independent value (MVP discipline, Article VIII).
- The customer/invoice/settings model is intentionally designed so Quote and Order can reuse `Customer`, the line-based document shape, and the posting infrastructure later without breaking Invoice APIs.

## 3. Account Mapping: How To Avoid Hard-Coded Account IDs

Alternatives considered:

1. **Name/type lookup** (e.g., find any `Asset` account named "Accounts Receivable"). Rejected: brittle under renames and duplicates; a second "Sales Revenue" account silently corrupts postings.
2. **Auto-provision default accounts** on first post. Rejected: conflicts with user-managed charts of accounts, risks duplicates, and mixes configuration with accounting writes.
3. **Per-tenant mapping model (`SalesAccountingSettings`)** with explicit FK fields to `Account`, validated tenant-scoped and type-checked. **Selected.** It is explicit, safe, auditable, and follows the existing per-tenant settings/ownership patterns.

Posting requires a complete mapping; the error on incomplete mapping is generic (no disclosure of which accounts exist).

## 4. Invoice Lifecycle and Numbering

- **Number**: user-supplied at creation, enforced unique per tenant via `UniqueConstraint(tenant, number)`. This mirrors the existing `JournalEntry.reference` convention (user-supplied + unique per tenant) and avoids introducing a numbering sequence service in the foundation feature. Auto-numbering is a documented future enhancement.
- **Lifecycle**: `Draft` (editable, deletable) → `Posted` (immutable, linked to exactly one journal entry). This matches the "no direct edits to posted entries" rule in Constitution Article II.

## 5. Posting: Idempotency, Transactions, Balanced Entry

- **Idempotency**: the invoice holds `posted_journal` (OneToOne to `JournalEntry`). A second post is rejected before any write; the existing linked entry is never re-created.
- **All-or-nothing**: the posting service runs inside `transaction.atomic()`. Invoice status update, journal entry, and journal lines are created, then committed together. Any validation failure raises before commit so no partial writes persist.
- **Balanced by construction**: entry lines are `Dr AR = total`, `Cr Revenue = subtotal − discount`, `Cr VAT = tax`. Because `total = (subtotal − discount) + tax` by definition, the entry is always balanced without floating-point tolerance issues. Zero-tax invoices omit the VAT line. This also requires `total > 0` at the invoice level, so drafts with `discount ≥ subtotal` (zero/negative total) are rejected at validation — never reaching the accounting layer.
- **Collision safety**: `reference` uses the `SALES-INV-` prefix; on the unlikely `IntegrityError` of a colliding manual journal reference, posting fails safely with a generic error and the transaction rolls back.
- **Currency**: the accounting architecture has no currency field, so Sales is single-currency for this feature (no currency column). Multi-currency is deferred until the ledger supports it.

## 6. Decimal Handling

All money fields (invoice and line amounts, journal entry lines) are `DecimalField(max_digits=19, decimal_places=4)`. Computations use `decimal.Decimal`; the totals stored on the invoice are recomputed from line values at the service boundary so stored amounts and posted entries always agree. No `float` arithmetic is used for money anywhere in the sales path.

## 7. Permissions

Reuses the existing roles without adding new ones:

| Action | Admin | Accountant | Manager |
|---|---|---|---|
| View customers / invoices | ✓ | ✓ | ✓ |
| Create / edit customers, invoices (draft) | ✓ | ✓ | ✗ |
| Post invoices | ✓ | ✓ | ✗ |
| Configure sales accounting mapping | ✓ | ✗ | ✗ |

Implemented as `CanViewSales`, `CanManageSales`, `CanPostSalesInvoice`, `CanConfigureSales` in `apps/sales/permissions.py`, mirroring the accounting permission style.

## 8. API Shape

- Routers under `/api/v1/sales/` following the accounting router pattern:
  - `customers` → `CustomerViewSet`
  - `invoices` → `SalesInvoiceViewSet` (list/create/retrieve, patch for drafts, `POST invoices/{id}/post/`)
  - `settings` → `SalesSettingsView` (GET/PUT, admin only)
- Errors follow the existing DRF JSON style (`{"detail": ...}`, 400/403/404/405).

## 9. Frontend

- `services/salesService.js` mirrors `accountingService.js`.
- Pages: `CustomersPage`, `SalesInvoicesPage` (list + create/edit form + detail + post action), `SalesSettingsPage` (admin, account mapping pickers). `SalesNav` mirrors `AccountingNav`.
- Reuses inline-style + CSS variable conventions. Manager sees read-only views (no create/post buttons). No new design language.

## 10. Deferred (Documented)

- Sales Quote, Sales Order
- Payments / receipts (customer payment posting)
- Inventory / product catalog references on lines
- Tax/VAT rate configuration (rates are entered per line for now)
- Auto invoice numbering
- Frontend automated tests (no test framework exists; verification is build + lint)