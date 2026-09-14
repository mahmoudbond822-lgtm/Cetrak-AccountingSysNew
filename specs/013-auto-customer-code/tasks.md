# Tasks - Automatic Customer Code on Create

**Feature**: 013-auto-customer-code
**Branch**: 013-auto-customer-code
**Created**: 2026-09-14

## Phase 1 - Setup

- [X] T001 Create feature structure and register app if not already done per specs/013-auto-customer-code/plan.md
- [X] T002 [P] Add frontend route/scaffold reference for customers create without code field (frontend/src/components/sales/customers/CustomerModal.jsx)

## Phase 2 - Foundational

- [X] T003 [US1] Backend: add tenant-scoped auto-code service in backend/apps/sales/services.py (mint next `CUS-{n}` unique per tenant)
- [X] T004 [US1] Backend: serializer mints code when blank on create in backend/apps/sales/serializers.py (remove "required" on code)

## Phase 3 - User Story 1 - Customer created without typing a code (P1)

- [X] T005 [US1] Frontend: remove `Code *` manual input from create form (Code read-only on edit) in frontend/src/components/sales/customers/CustomerModal.jsx
- [X] T006 [US1] Frontend: create payload omits `code`; list displays auto-minted code in frontend/src/pages/sales/CustomersPage.jsx
- [X] T007 [US1] Backend test: create with blank code succeeds, returns non-blank tenant-unique code (backend/apps/sales/tests/test_auto_customer_code.py)

## Phase 4 - User Story 2 - Edits never change/blank the code (P2)
- [X] T008 [US2] Frontend: edit form shows code read-only, save never sends code in frontend/src/components/sales/customers/CustomerModal.jsx
- [X] T009 [US2] Backend test: edit preserves code; blank code on edit is ignored (not regenerated, not blanked) backend/apps/sales/tests/test_auto_customer_code.py

## Phase 5 - User Story 3 - Codes stay tenant-unique & collision-safe (P3)
- [X] T010 [US3] Backend: collision-aware next-code (skip existing/race retry) in backend/apps/sales/services.py
- [X] T011 [US3] Backend test: concurrent creates in a tenant produce distinct codes; cross-tenant no clash backend/apps/sales/tests/test_auto_customer_code.py

## Phase 6 - Polish & Cross-Cutting
- [X] T012 Run full backend suite (apps/) + frontend build + lint; confirm 0 new problems in specs/013-auto-customer-code/report.md
