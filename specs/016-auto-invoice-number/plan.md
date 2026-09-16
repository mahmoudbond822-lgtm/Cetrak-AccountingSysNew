# Implementation Plan: Auto Invoice Number

**Branch**: `016-auto-invoice-number` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-auto-invoice-number/spec.md`

## Summary

Creating a sales or purchase invoice currently fails with `{"number":["Invoice number is required."]}` when no number is typed. This plan mirrors Features 014/015: the backend mints the next per-business number (`INV-0001`, +1 per saved invoice) at save time, and the create dialogs show that number in a visible but disabled field. Preview is a hint only — authoritative assignment happens at save, skipping collisions, immutable after creation (draft and posted). Two adaptations to the invoice domain: sequences are **per-type** (sales and purchase each run their own `INV-` sequence, matching their separate uniqueness rules), and explicit duplicates stay **rejected** (existing "already exists" behavior, unlike the customer/vendor idempotent path). No schema migration; behavior + presentation only.

## Technical Context

**Language/Version**: Python 3.14 backend (Django + DRF); React frontend (existing toolchain, npm)

**Primary Dependencies**: Django, Django REST Framework (backend); React (frontend)

**Storage**: SQLite for dev/test (`config.settings.test`); Postgres via Docker Compose for prod-like env. No schema change — `SalesInvoice.number` / `PurchaseInvoice.number` CharField(50) with existing per-tenant unique constraints reused as-is.

**Testing**: `py -m pytest apps/ -q` with `DJANGO_SETTINGS_MODULE=config.settings.test` (backend, currently 381 passed / 1 skipped); `npm run build` + `npm run lint` (frontend, 18 pre-existing lint problems)

**Target Platform**: Web application — Django API (`backend/`) + React SPA (`frontend/`), served via Docker Compose

**Project Type**: Web application (backend + frontend)

**Performance Goals**: No new target — mint is one extra indexed lookup (max numeric suffix among the tenant's invoices of that type) per invoice create; negligible vs. request cost (invoice creation already writes header + lines in one transaction)

**Constraints**: Behavior-only change (no migration; `makemigrations --check` must stay clean); tenant isolation must hold on every query; draft/posted lifecycle untouched; journal-reference derivation (`SALES-INV-{number}`, `PUR-INV-{number}`) untouched; no push/deploy (commit via hook only)

**Scale/Scope**: Two dialogs (`InvoiceForm`, `PurchaseInvoiceForm`), two pages (`InvoicesPage`, `PurchaseInvoicesPage` preview helpers + notices), two service paths (`SalesInvoiceService.create_draft`, `PurchaseInvoiceService.create_draft` + per-type next-number helpers), two serializer paths; per-business per-type sequential numbers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Multi-Tenancy (non-negotiable) | PASS | Mint scans only the tenant's invoices of that type; uniqueness enforced by existing per-table constraints |
| II. Accounting Integrity | PASS | No journal/ledger logic touched; numbers immutable after creation; draft/posted lifecycle untouched; post still derives references from stored number |
| III. API Rules | PASS | RESTful POST/PATCH; auth required; consistent JSON; 201 on create; explicit duplicates keep existing 400 "already exists" |
| IV. Code Standards (services layer) | PASS | Mint lives in `SalesInvoiceService` / `PurchaseInvoiceService` (next-number helpers + blank→mint in `create_draft`); views stay thin |
| V. AI Safety | N/A | No AI surface in this feature |
| VI. Security | PASS | Tenant isolation enforced at service + middleware layers; no cross-tenant sequence leak |
| VII. Performance | PASS | Single indexed max-suffix scan per create; no async work needed |
| VIII. MVP Discipline | PASS | Scoped to the two invoice create dialogs + mint paths; payments/adjustments numbering untouched |

Post-design re-check: no new apps, no schema change, no new endpoints — all gates still PASS. Nothing to justify in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/016-auto-invoice-number/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── invoice-create.md
├── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── apps/sales/
│   ├── models.py        # SalesInvoice (unchanged schema)
│   ├── serializers.py   # SalesInvoiceSerializer: number optional/allow_blank, blank → mint
│   ├── services.py      # SalesInvoiceService.next_number + blank→mint in create_draft; update_draft ignores number
│   ├── views.py         # Sales create: pass through optional number; update: stop passing number
│   └── tests/
│       └── test_auto_invoice_number.py   # NEW: sales cases (sequence, blank-mint, locked, cross-tenant, stale, duplicate-reject)
├── apps/purchases/
│   ├── models.py        # PurchaseInvoice (unchanged schema)
│   ├── serializers.py   # PurchaseInvoiceSerializer: number optional/allow_blank, blank → mint
│   ├── services.py      # PurchaseInvoiceService.next_number + blank→mint in create_draft; update_draft ignores number
│   ├── views.py         # Purchase create: pass through optional number; update: stop passing number
│   └── tests/
│       └── test_auto_invoice_number.py   # NEW: purchase cases (same matrix)

frontend/
├── src/
│   ├── components/sales/invoices/
│   │   └── InvoiceForm.jsx               # Create: disabled Number preview; payload omits number; edit: read-only
│   ├── components/purchases/invoices/
│   │   └── PurchaseInvoiceForm.jsx       # Same pattern for purchase side
│   ├── pages/sales/
│   │   └── InvoicesPage.jsx              # next-number helper + assigned-number notice
│   └── pages/purchases/
│       └── PurchaseInvoicesPage.jsx      # Same pattern for purchase side
```

**Structure Decision**: Web application layout (Option 2). Mirrors the proven 014/015 shape on both invoice sides; per-type helpers keep the sales/purchases services decoupled (no cross-app scan), matching the per-table uniqueness model.

## Complexity Tracking

No constitution violations — table intentionally empty.
