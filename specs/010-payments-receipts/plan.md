# Implementation Plan: Payments & Receipts (Feature 010)

## Goal

Allow accountants to record customer payments against **posted** sales invoices. Posting a payment atomically books a balanced Journal Entry — **Dr** the payment's `cash_account` (Asset), **Cr** the tenant's configured `accounts_receivable` from Sales Settings — locks the invoice row to prevent overpayment races, and is idempotent (no double posting). Partial and multiple payments are supported with a derived outstanding balance; overpayment is always rejected. Drafts are editable/deletable; posted payments are immutable (reversal deferred, correction = manual JE).

## Constraints (from prior artifacts + Constitution)

- Money = `Decimal(19,4)`; **no `float` in any money path**.
- `transaction.atomic()` around every payment-posting write; `select_for_update()` on the invoice row.
- Tenant isolation on every read via `.for_tenant(request.tenant_id)`; generic errors on cross-tenant references.
- Reuse `TenantScopedAccountField` for `cash_account`.
- Reuse existing sales permissions (`CanViewSales`, `CanManageSales`, `CanPostSalesInvoice`); no new roles/permissions.
- No schema changes in `apps/accounting`; new table lives in `apps/sales`.
- No new frontend dependencies; follow Feature 009 page/form patterns.

## Phases

### Phase 1 — Model & migration
- Add `Payment` model (`Payment.Status`, fields, constraints, indexes) + `sales_payment` table migration `0002`.
- No changes to `SalesInvoice`, `SalesSettings`, or accounting models.

### Phase 2 — Services (`PaymentService`)
- `invoice_paid_amount(invoice)` / `invoice_outstanding(invoice)` (post-only aggregate, Decimal math, clamp at 0).
- `create_draft(...)`: validations (invoice exists+posted+tenant, number unique later at DB, amount > 0 and ≤ outstanding, account asset already validated at serializer; service re-checks), returns draft.
- `update_draft(...)`: only Draft; re-validate amount vs outstanding after edit.
- `delete_draft(id)`.
- `post_payment(id)`: idempotency guard (`status != Draft` → error); settings/AR validation (tenant, active, Asset); `transaction.atomic()` + `select_for_update(invoice)`; recompute outstanding in Decimal; overpayment → error; create posted JE (reference `PAY-INV-{invoice}-{number}`, Dr cash, Cr AR, balanced); link `journal_entry`, set `Posted`, `posted_at`; `IntegrityError` → duplicate-reference error.

### Phase 3 — Serializers & views
- `PaymentSerializer` (create/update/list), nested invoice summary (number, customer, total, `paid_amount`, `outstanding_balance`), brand `cash_account` via `TenantScopedAccountField`.
- Additive read-only `paid_amount` / `outstanding_balance` on `SalesInvoiceSerializer`.
- `PaymentViewSet` (list/create/retrieve/update/destroy) + `post_payment` action mirroring `post_invoice`.
- Wire URLs `api/v1/sales/payments/`, `payments/{id}/`, `payments/{id}/post_payment/`; permissions map from contracts §9.

### Phase 4 — Tests (`apps/sales/tests/test_payments_api.py`)
- Full story matrix from research §5 (happy path, partial/multiple, overpayment, status guards, tenant isolation, account/settings validation, number uniqueness, idempotency) plus regression run.

### Phase 5 — Frontend
- `salesService` payments CRUD + `postPayment`.
- `PaymentsPage` (list with outstanding + status), payment form page (invoice picker filtered to posted, outstanding display, amount/method/cash_account/reference/notes), edit, delete, post-confirm dialog.
- `SalesNav` "Payments" entry; routes `/sales/payments`, `/sales/payments/new`, `/sales/payments/:id`.

### Phase 6 — Docs & verification
- Update AGENTS.md (feature complete), spec checklists (requirements, tasks, quickstart), run build/lint/tests, commit.

## Decisions locked (see research.md)

| # | Decision |
|---|---|
| D1 | `Payment` in `apps/sales` |
| D2 | Draft → Posted lifecycle; no reversal in v1 |
| D3 | Outstanding = total − Σ posted; overpayment rejected at create **and** at post (row-locked) |
| D4 | Cr always = settings `accounts_receivable`; Dr = per-payment `cash_account` |
| D5 | User-supplied numbering, unique per tenant |
| D6 | No new settings fields |
| D7 | Additive invoice fields (non-breaking) |
| D8 | Generic cross-tenant errors |

## Risks
See research.md §3. Notable: concurrency (mitigated by row lock + unique reference), AR mismatch (D4), double booking (status guard + uniqueness), additive-serializer regression (full suite re-run).

## Definition of Done

1. `python manage.py makemigrations` produces a single clean migration for the payment table.
2. Posting a payment creates **exactly one** balanced JE (Dr cash, Cr settings-AR) and flips payment to `Posted`.
3. Partial/multiple payments update `outstanding_balance` correctly (10,000 → 4,000 → 0 examples in spec §US2 pass).
4. Overpayment (including race) is rejected at both create and post; no orphan JE ever.
5. Re-posting the same payment is rejected and never creates a second JE.
6. Cross-tenant invoice/account access denied with generic errors; tenant isolation tests pass.
7. Inactive/non-Asset/foreign cash accounts rejected via `TenantScopedAccountField`.
8. Settings without valid active AR → posting fails with config error; draft creation still works.
9. Posted payments are immutable (edit/delete → 400).
10. Backend suite green: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/ -q` (baseline 130 + new all pass).
11. Frontend: `npm run build` passes; new files lint-clean (`npm run lint` still shows only the 16 pre-existing errors).
12. Spec artifacts complete (spec, research, data model, contracts, plan, tasks, quickstart, checklist) and committed.