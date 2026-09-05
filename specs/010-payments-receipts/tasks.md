# Implementation Tasks: Payments & Receipts (Feature 010)

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

## Phase 1 — Model & migration

- [x] `T-001` Add `Payment` model to `backend/apps/sales/models.py` (fields per data-model.md §1: `number`, `invoice` FK PROTECT, `payment_date`, `amount` Decimal(19,4), `method` choices Cash/Bank Transfer/Card/Check, `cash_account` FK Account PROTECT, `reference`, `notes`, `status` Draft/Posted, `journal_entry` OneToOne PROTECT null, `posted_at`; constraints `unique (tenant, number)`; indexes `(tenant, status)`, `(invoice)`).
- [x] `T-002` Generate migration `backend/apps/sales/migrations/0002_payment.py` (`makemigrations sales`); confirm no changes outside `apps/sales`.
- [x] `T-003` Verify migration applies cleanly: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py manage.py migrate --check`+`makemigrations --check --dry-run` (no pending changes).

## Phase 2 — Services (`backend/apps/sales/services.py`)

- [x] `T-004` `PaymentService.invoice_paid_amount(invoice)` — Decimal sum of POSTED payments for the invoice (tenant-scoped).
- [x] `T-005` `PaymentService.invoice_outstanding(invoice)` — `max(total − paid, 0)`, Decimal.
- [x] `T-006` `PaymentService.create_draft(...)` — validate invoice exists+tenant+`Posted`, `amount > 0`, `amount ≤ outstanding`; create Draft; `IntegrityError` → `ValueError("Payment number already exists.")`.
- [x] `T-007` `PaymentService.update_draft(...)` — only Draft; re-validate amount vs outstanding (same checks as create); return updated.
- [x] `T-008` `PaymentService.delete_draft(...)` — only Draft; delete; never touches JEs.
- [x] `T-009` `PaymentService.post_payment(...)` — idempotency guard; settings AR validation (exists, tenant, active, Asset); `transaction.atomic()` + `select_for_update(invoice)`; Decimal outstanding recompute; overpayment → `ValueError`; create posted JE (`PAY-INV-{invoice.number}-{payment.number}`, Dr cash, Cr AR, balanced, date=payment_date); link `journal_entry`, set `Posted`, `posted_at`; `IntegrityError` → duplicate-reference error.
- [x] `T-010` No `float` anywhere in new service code (Decimal only).

## Phase 3 — Serializers, views, URLs

- [x] `T-011` `PaymentSerializer` (create/update/list/retrieve) with nested invoice summary (id, number, customer, total, `paid_amount`, `outstanding_balance`); `cash_account` via `TenantScopedAccountField`.
- [x] `T-012` Add read-only `paid_amount` + `outstanding_balance` to `SalesInvoiceSerializer` (additive, non-breaking).
- [x] `T-013` `PaymentViewSet` — list/create/retrieve/update/destroy + `post_payment` action (mirror `post_invoice`); all tenant-scoped; permission map per contracts §9.
- [x] `T-014` Wire URLs: `payments/`, `payments/{id}/`, `payments/{id}/post_payment/` under `api/v1/sales/`.
- [x] `T-015` Sanity-check via quickstart scenarios (spec §quickstart).

## Phase 4 — Tests (`backend/apps/sales/tests/test_payments_api.py`)

- [x] `T-016` Happy path: invoice → post → draft payment → post payment → one balanced JE, outstanding 0.
- [x] `T-017` Partial/multiple: 10,000 → pay 4,000 (outstanding 6,000 both invoice+payment payload) → pay 6,000 (0); third payment rejected.
- [x] `T-018` Overpayment: create + post amount > outstanding (both directions) → 400 stable message, no JE.
- [x] `T-019` Guards: draft editable/deletable; posted immutable; posting a draft-invoice payment rejected; posting already-posted rejected (idempotency), single JE remains.
- [x] `T-020` Tenant isolation: foreign invoice, foreign account, foreign payment → generic errors, no leakage.
- [x] `T-021` Account validation: inactive, non-Asset, foreign → validation error.
- [x] `T-022` Settings validation: missing/inactive AR account → posting fails, draft create still OK.
- [x] `T-023` Number uniqueness → 400.
- [x] `T-024` Regression: full backend suite green (baseline 130 + 23 new = 153 passing).

## Phase 5 — Frontend

- [x] `T-025` `frontend/src/services/salesService.js` — payments list/create/update/delete/postPayment; invoice list already returns `paid_amount`/`outstanding_balance`.
- [x] `T-026` `PaymentsPage.jsx` — list (number, customer, invoice, date, method, amount, status, invoice outstanding), create button, delete draft, post-confirm dialog for draft.
- [x] `T-027` `PaymentForm.jsx` — invoice picker (posted only, shows outstanding), amount with client-side ≤ outstanding check, method select, cash account select (Asset accounts), reference/notes; new + edit modes.
- [x] `T-028` List route `/sales/payments` + `SalesNav` "Payments" entry; create/edit/post handled via the page modal (mirrors the existing customers/invoices pattern — no separate `/new` or `/:id` routes).
- [x] `T-029` `npm run build` passes; new files lint-clean (`npm run lint` — only the 16 pre-existing errors remain).

## Phase 6 — Docs & close-out

- [x] `T-030` Update `specs/010-payments-receipts/tasks.md` all `[x]`; write `report.md`.
- [x] `T-031` Update `AGENTS.md` to Feature 010 IMPLEMENTATION COMPLETE (with next steps + quick reference).
- [x] `T-032` Update checklist `specs/010-payments-receipts/checklists/requirements.md` (all verified).
- [x] `T-033` Final verification: backend suite, `npm run build`, `npm run lint` (baseline errors only), `git status` review, commit (auto-commit).