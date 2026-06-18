# Feature Specification: Multi-Tenancy Hardening

**Feature Branch**: `004-multi-tenancy-hardening`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Multi-Tenancy Hardening — Execution Plan with file-by-file changes for tenant FK integrity, middleware validation, query indexing, and explicit tenant scoping"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant data isolation is enforced at the application layer (Priority: P1)

A developer or API consumer attempts to access or create data for a tenant they do not belong to. The system proactively rejects invalid cross-tenant access rather than relying on each service method to remember the filter.

**Why this priority**: The constitution (Articles I and VI) mandates tenant isolation at both the database and application layer. The current passive middleware trusts the caller completely — a single forgotten filter in any service method leaks data across tenants. Active enforcement closes this class of bug permanently.

**Independent Test**: An authenticated user sends a request with a tenant ID they have no membership for. The request is rejected with a 403 error before reaching any view or service method, regardless of which endpoint is called.

**Acceptance Scenarios**:

1. **Given** an authenticated user with membership in tenant A only, **When** they send a request with tenant A's ID, **Then** the request proceeds normally.
2. **Given** an authenticated user with membership in tenant A only, **When** they send a request with tenant B's ID (or a non-existent tenant ID), **Then** the request is rejected with a 403 Forbidden response.
3. **Given** an unauthenticated request to a public endpoint (register, login), **When** the request has no tenant context, **Then** it is allowed through without tenant enforcement.

---

### User Story 2 - Tenant-filtered queries perform consistently as data grows (Priority: P2)

As tenants add members over time, listing members, checking admin status, and other tenant-scoped queries remain fast regardless of total system size.

**Why this priority**: The constitution (Article VII) requires appropriate indexes on all WHERE clauses. Membership queries filtered by `tenant_id` are the most frequent database operation; missing an index here causes linear degradation.

**Independent Test**: A tenant with 1000 members can list all members and perform admin checks in under 100ms, regardless of how many other tenants and members exist in the system.

**Acceptance Scenarios**:

1. **Given** a tenant with 1000 members and a system with 10,000+ total members across all tenants, **When** an admin lists all members, **Then** the query completes in under 100ms.
2. **Given** the same scale, **When** an admin performs a role change or member removal (which checks admin count), **Then** each admin-count query completes in under 50ms.

---

### User Story 3 - Developers cannot accidentally create tenant-scoped records without a tenant (Priority: P3)

A developer adding a new model that extends `TenantScopedModel` is prevented at the database level from creating records with a null `tenant_id`, eliminating a class of data integrity bugs.

**Why this priority**: The current `null=True` on the abstract base means any future tenant-scoped model could silently accept null tenant references. Enforcing non-null at the schema level prevents orphan records before they happen.

**Independent Test**: An attempt to insert a tenant-scoped record with a null tenant is rejected by the database, and all existing tenant-scoped records have a non-null tenant reference.

**Acceptance Scenarios**:

1. **Given** the Invitation model (which extends TenantScopedModel), **When** attempting to save an invitation without a tenant, **Then** the database rejects the operation.
2. **Given** any future model extending TenantScopedModel, **When** it is created, **Then** the tenant field is automatically required at the database level.

---

### Edge Cases

- What happens when a request has a valid JWT with tenant_id but the user was removed from that tenant after the token was issued? → The middleware queries the current membership table, so the removed user is rejected with 403. They must re-authenticate to get a new token.
- What happens when an admin switches tenants via the tenant switch endpoint? → The switch endpoint issues a new JWT with the new tenant_id. The middleware validates membership for the new tenant on the next request.
- What happens to users with multiple tenants who have not yet selected one (no tenant_id in JWT)? → The middleware falls back to the X-TENANT-ID header for these users. If neither JWT nor header has a tenant_id and the endpoint requires authentication, the request is rejected.
- What happens to existing invitation records that may have null tenant? → The migration enforces NOT NULL and will fail if any such records exist. A data cleanup step should run before the migration to either assign a tenant or delete orphaned invitations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reject any authenticated request whose tenant context does not match an active membership for the requesting user.
- **FR-002**: Public endpoints (registration, login, token refresh) MUST be exempt from tenant enforcement.
- **FR-003**: The tenant context MUST be resolved from the JWT token claims first, falling back to the X-TENANT-ID header.
- **FR-004**: The resolved tenant ID MUST be validated as a proper UUID format before any database query uses it.
- **FR-005**: The Membership.tenant foreign key MUST have a database index to ensure tenant-filtered queries perform efficiently.
- **FR-006**: All models extending `TenantScopedModel` MUST enforce a non-null tenant at the database level.
- **FR-007**: The service layer MUST use an explicit `for_tenant()` query method for all tenant-scoped queries, making the scope visible in code.
- **FR-008**: Error responses for invalid or unauthorized tenant context MUST be uniform 403 Forbidden responses with a clear message.

### Key Entities

- **Tenant**: An organization or company whose data is isolated from all other tenants. Identified by UUID.
- **Membership**: The link between a User and a Tenant, defining the user's role within that tenant. The source of truth for tenant access validation.
- **TenantScopedModel**: Abstract base class for all models whose data belongs to a specific tenant. Enforces the presence of a `tenant` foreign key.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cross-tenant access attempts are rejected in under 200ms, before any business logic executes.
- **SC-002**: Tenant-filtered membership queries (list members, admin count check) execute in under 50ms at a scale of 10,000 total members across all tenants.
- **SC-003**: Zero tenant-scoped database records can exist with a null tenant reference after the migration is applied.
- **SC-004**: All existing service methods that filter by `tenant_id` use the explicit `for_tenant()` pattern.
- **SC-005**: All existing 36 authentication and team management tests continue to pass without modification.

## Assumptions

- The existing JWT authentication flow sets `request.auth` before middleware runs (Django REST Framework processes authentication in the View, but DRF's `JWTAuthentication` runs during view processing, not middleware). If `request.auth` is not available during middleware execution, the middleware falls back to parsing the `Authorization` header directly or relies solely on the `X-TENANT-ID` header.
- No tenant-scoped records with null tenant exist in the development or production databases. If any exist, a one-time data migration must assign or delete them before the schema migration.
- The `X-TENANT-ID` header continue to be sent by the frontend for multi-tenant users who have not selected a tenant yet (no tenant_id in JWT).
- The existing test suite uses SQLite exclusively. The index addition and NOT NULL constraint can be verified via schema inspection on SQLite, but performance benchmarks require PostgreSQL-based testing.
