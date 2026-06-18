# Quickstart: Multi-Tenancy Hardening

**Phase**: 1 — Validation Guide

**Date**: 2026-06-18

## Prerequisites

- Backend running at `localhost:8000` (or test suite environment)
- PostgreSQL database (for index and NOT NULL validation; SQLite works for functional tests)
- Python 3.14+ with dependencies installed

## Scenario 1 — Active Middleware Rejects Cross-Tenant Access

**Purpose**: Verify that an authenticated user cannot access a tenant they don't belong to.

1. Register two users in separate tenants:
   ```
   POST /api/v1/auth/register/
   {"email": "alice@a.com", "password": "testpass123", "company_name": "TenantA"}
   
   POST /api/v1/auth/register/
   {"email": "bob@b.com", "password": "testpass123", "company_name": "TenantB"}
   ```
2. Extract Alice's JWT and Bob's tenant ID
3. Send Alice's JWT with Bob's tenant ID:
   ```
   GET /api/v1/team/members/
   Authorization: Bearer <alice-jwt>
   X-TENANT-ID: <bob-tenant-id>
   ```
4. **Expected**: `403 Forbidden` with `{"detail": "You do not have access to this tenant."}`

## Scenario 2 — Middleware Allows Valid Tenant Access

**Purpose**: Verify that legitimate requests pass through.

1. Use Alice's JWT with Alice's own tenant ID:
   ```
   GET /api/v1/team/members/
   Authorization: Bearer <alice-jwt>
   X-TENANT-ID: <alice-tenant-id>
   ```
2. **Expected**: `200 OK` with member list

## Scenario 3 — Middleware Rejects Invalid UUID

**Purpose**: Verify that an invalid tenant ID format is caught early.

1. Send request with malformed tenant ID:
   ```
   GET /api/v1/team/members/
   Authorization: Bearer <alice-jwt>
   X-TENANT-ID: not-a-uuid
   ```
2. **Expected**: `403 Forbidden` with `{"detail": "Invalid tenant ID format."}`

## Scenario 4 — Tenant-Filtered Query Performance

**Purpose**: Verify that tenant-filtered queries use the new index.

1. Run `EXPLAIN ANALYZE` on the membership query:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM accounts_membership WHERE tenant_id = '<tenant-uuid>';
   ```
2. **Expected**: The plan shows an `Index Scan` on `accounts_membership_tenant_id` (not a `Seq Scan`).

## Scenario 5 — NOT NULL Constraint on Invitation.tenant

**Purpose**: Verify that tenant-scoped records cannot be created without a tenant.

1. Attempt to insert an invitation without a tenant:
   ```sql
   INSERT INTO accounts_invitation (id, email, role, token, expires_at, accepted_at, created_at, updated_at)
   VALUES (gen_random_uuid(), 'test@test.com', 'Accountant', 'tok123', NOW() + INTERVAL '7 days', NULL, NOW(), NOW());
   ```
2. **Expected**: PostgreSQL rejects with `ERROR: null value in column "tenant_id" violates not-null constraint`.

## Scenario 6 — Test Suite Regression

**Purpose**: Verify that all existing tests still pass.

1. Run the test suite:
   ```bash
   cd backend
   py -m pytest apps/accounts/tests/ -v
   ```
2. **Expected**: All 36 tests pass.
