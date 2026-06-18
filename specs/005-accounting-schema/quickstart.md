# Quickstart: Accounting Schema

**Phase**: 1 — Validation Guide

**Date**: 2026-06-18

## Prerequisites

- Backend running at `localhost:8000`
- PostgreSQL database (SQLite works for functional tests; index and CHECK constraint tests need PostgreSQL)
- Python 3.14+ with dependencies installed
- A registered user with an active tenant and `Admin` membership role

## Scenario 1 — Create a Chart of Accounts Hierarchy

**Purpose**: Verify that accounts can be created with parent-child relationships and rendered as a tree.

1. Create a root account:
   ```
   POST /api/v1/accounting/accounts/
   Authorization: Bearer <jwt>
   X-TENANT-ID: <tenant-id>
   {
       "name": "Assets",
       "type": "Asset",
       "parent_id": null
   }
   ```
   **Expected**: `201 Created` with the new account.

2. Create a child account using the parent's UUID:
   ```
   POST /api/v1/accounting/accounts/
   Authorization: Bearer <jwt>
   X-TENANT-ID: <tenant-id>
   {
       "name": "Cash",
       "type": "Asset",
       "parent_id": "<assets-uuid>"
   }
   ```
   **Expected**: `201 Created`.

3. Fetch the tree:
   ```
   GET /api/v1/accounting/accounts/?tree=true
   ```
   **Expected**: `200 OK` — response shows `Assets` as a root node with `Cash` nested under `children`.

## Scenario 2 — Create a Balanced Journal Entry

**Purpose**: Verify that a valid journal entry with two lines (total debits = total credits) is created successfully.

1. Create a journal entry:
   ```
   POST /api/v1/accounting/journal-entries/
   Authorization: Bearer <jwt>
   X-TENANT-ID: <tenant-id>
   {
       "date": "2026-06-18",
       "description": "Record sale of services",
       "reference": "INV-001",
       "lines": [
           {"account_id": "<cash-uuid>", "debit": "1000.0000", "credit": "0.0000"},
           {"account_id": "<revenue-uuid>", "debit": "0.0000", "credit": "1000.0000"}
       ]
   }
   ```
   **Expected**: `201 Created` with the entry header and two lines.

2. Fetch the entry detail:
   ```
   GET /api/v1/accounting/journal-entries/<entry-uuid>/
   ```
   **Expected**: `200 OK` — response includes both lines with correct amounts.

## Scenario 3 — Reject an Unbalanced Journal Entry

**Purpose**: Verify that the balanced-entry rule (constitutional hard requirement) rejects unbalanced entries.

1. Attempt to create an unbalanced entry:
   ```
   POST /api/v1/accounting/journal-entries/
   Authorization: Bearer <jwt>
   X-TENANT-ID: <tenant-id>
   {
       "date": "2026-06-18",
       "description": "Unbalanced entry",
       "reference": "INV-002",
       "lines": [
           {"account_id": "<cash-uuid>", "debit": "1000.0000", "credit": "0.0000"},
           {"account_id": "<revenue-uuid>", "debit": "0.0000", "credit": "500.0000"}
       ]
   }
   ```
   **Expected**: `400 Bad Request` with `{"non_field_errors": ["Journal entry is not balanced. Total debits (1000.00) do not equal total credits (500.00)."]}`.

## Scenario 4 — Journal Entry Immutability

**Purpose**: Verify that once a journal entry is created, it cannot be modified or deleted.

1. Attempt to modify an existing entry:
   ```
   PATCH /api/v1/accounting/journal-entries/<entry-uuid>/
   {"description": "Modified description"}
   ```
   **Expected**: `405 Method Not Allowed` (or `400 Bad Request` if the endpoint doesn't exist at all — PATCH is not implemented for journal entries).

2. Attempt to delete an existing entry:
   ```
   DELETE /api/v1/accounting/journal-entries/<entry-uuid>/
   ```
   **Expected**: `405 Method Not Allowed`.

## Scenario 5 — Tenant Isolation

**Purpose**: Verify that accounts and journal entries are tenant-scoped and cross-tenant access is rejected.

1. Create an account in Tenant A.
2. Send a request for that account using Tenant B's context:
   ```
   GET /api/v1/accounting/accounts/<tenant-a-account-uuid>/
   Authorization: Bearer <user-with-membership-in-both-tenants>
   X-TENANT-ID: <tenant-b-id>
   ```
   **Expected**: `404 Not Found` (the account does not exist in Tenant B's scope).

## Scenario 6 — Test Suite Regression

**Purpose**: Verify that all existing tests still pass and new accounting tests run.

1. Run the full test suite:
   ```bash
   cd backend
   py -m pytest apps/accounts/tests/ apps/accounting/tests/ -v
   ```
   **Expected**: All 36 existing tests pass plus new accounting tests pass.

## References

- [API Contracts](./contracts/api.md) — Full request/response schemas
- [Data Model](./data-model.md) — Entity definitions and constraints
- [Spec](./spec.md) — Feature specification
