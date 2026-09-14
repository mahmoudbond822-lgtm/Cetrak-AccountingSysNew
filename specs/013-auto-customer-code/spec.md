# Feature Specification: Auto-Generated Customer Code

**Feature Branch**: `013-auto-customer-code`

**Created**: 2026-09-14

**Status**: Draft (awaiting review)

**Input**: User description: "when create customer make code automatic not user input"

## Overview

The Sales **Customers** module currently makes `code` a **required, user-entered
field** on customer creation: the create form has a `Code *` input
(`frontend/src/components/sales/customers/CustomerModal.jsx`), and the backend
rejects a blank code with `"Customer code is required."`
(`backend/apps/sales/serializers.py` `CustomerSerializer.validate_code`). Every
tenant customer must have a per-tenant-unique code
(`unique_customer_code_per_tenant` constraint on `models.Customer`).

This feature inverts that requirement: **the system generates the customer code
automatically at create time**, so a user creating a customer never has to think
up or type a code. The `code` stays tenant-uniquehare (the constraint is kept
unchanged) and remains immutable-on-edit once created.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a customer without typing a code (Priority: P1)

An admin/accountant opens Sales → Customers → **Create Customer**, fills in the
customer details (name / email / phone / tax id / address), and submits. The
`code` is **not** a form input they have to fill; the backend assigns a unique
auto-generated code and the new customer appears in the list with that code.

**Why this priority**: This is the entire point of the request — removing the
manual code input from the create flow is the single slice that delivers value.

**Independent Test**: Can be fully tested by creating a customer while leaving
the code blank/removed and confirming a non-blank, tenant-unique code is
assigned, persisted, and shown in the list.

**Acceptance Scenarios**:

1. **Given** the create-customer form, **When** the user enters a name and saves
   without providing a code, **Then** a customer is created with a non-blank,
   tenant-unique auto-generated `code` and no "code required" error.
2. **Given** the customers list, **When** a customer created without a code, **Then**
   its `code` column shows the auto-generated value.

---

### User Story 2 - Codes stay stable and unique (Priority: P2)

The auto-generated code must remain unique within the tenant and must not
collide with any user-supplied code already in the tenant or with the
tenant-wide document-numbering conventions already in use (e.g. `PUR-INV-{n}`).

**Why this priority**: Uniqueness and non-collision protect the FK references
from sales/purchase invoices and the ledger; broken codes would corrupt existing
customers.

**Independent Test**: Can be fully tested by creating several customers in a row,
trying a duplicate code across tenants, and confirming each resulting code is
distinct per tenant.

**Acceptance Scenarios**:

1. **Given** a tenant with existing customers (including user-entered codes),
   **When** new customers are created, **Then** each auto-generated code is
   unique within that tenant and distinct from the numbering used by invoices
   and other tenant entities.
2. **Given** a code collision attempt (the rare case where generation would hit
   an existing code), **When** creation is attempted, **Then** the system retries
   with the next candidate or rejects with a generic error — it must never save
   or return a duplicate code.

---

### User Story 3 - Codes are immutable on edit but visible (Priority: P3)

Once a customer exists, editing it (name, email, phone…) must **not** change or
blank its code; the code is read-only at edit time and visible in the list.

**Why this priority**: Safety net — prevents accidental code drift that would
break historical references. Lower priority than create because it only guards
against an already-created customer being changed.

**Independent Test**: Can be fully tested by editing an existing customer's name
and confirming the code is unchanged and still present.

**Acceptance Scenarios**:

1. **Given** an existing customer, **When** a user opens **Edit Customer** and
   changes the name, **Then** the `code` is unchanged and remains unique.
2. **Given** the edit form, **When** the user saves with an empty/blank code
   field, **Then** the save succeeds and the existing code is preserved (it is
   never blanked or regenerated on edit).

---

### Edge Cases

- Creating a customer inside a tenant that already has a code equal to the next
  auto-generated value → generation must skip/retry to avoid the unique
  constraint/duplicate.
- A user-created code that collides with a future auto-generated value → the
  auto-generator must be collision-aware, not sequential-buggy.
- Creating without a code at **all** (empty string, whitespace, `None`) → all
  treated the same: auto-generate.
- Two tenants creating "first customers" concurrently → each gets its own
  sequence; no cross-tenant interference (codes are per-tenant unique).
- Bulk/rapid customer creates in one tenant → no two rows receive the same
  generated code (concurrency-safe generation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support creating a customer **without** a manually
  entered `code`.
- **FR-002**: System MUST auto-generate a non-blank, tenant-unique `code` for a
  customer whose `code` is empty/blank on create.
- **FR-003**: The auto-generated code MUST remain unique within the tenant
  (`unique_customer_code_per_tenant` constraint is kept) and MUST NOT collide
  with user-entered codes or the tenant's existing document-numbering
  conventions.
- **FR-004**: On **edit**, System MUST preserve the customer's existing `code` —
  it MUST NOT be blanked, regenerated, or made editable-required.
- **FR-005**: The create form MUST NOT require `code` input from the user;
  existing validation MUST NOT reject a create with a blank `code`.
- **FR-006**: System MUST support per-tenant numbering prefixes (e.g.
  `CUS-{n}`) so different tenants can use different prefixes if needed.
- **FR-007**: Auto-generation MUST be concurrency-safe — two concurrent creates
  in the same tenant MUST NOT yield the same code.

**Requirements requiring clarification**: none — the numbering prefix/format is
left as a documented default (`CUS-{n}` per tenant, sequential) reviewed at
implementation, and the tenant-scoped uniqueness behaviour is already enforced
by the existing model constraint.

### Key Entities

- **Customer**: tenant-scoped sales customer. `code` (CharField, per-tenant
  unique), `name`, `email`, `phone`, `tax_id`, `address`, `is_active`. Unchanged
  schema; this feature changes **who** supplies `code` (auto vs manual), not the
  entity.
- **Tenant**: owns customers and codes; codes are unique **per tenant**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Creating a customer with a blank code succeeds 100% of the time
  with no "code required" error, and the returned customer has a non-blank,
  unique code.
- **SC-002**: 100% of created customers are immediately visible in the Customers
  list with a displayed code.
- **SC-003**: 0 customer-code collisions occur across the tenant after this
  feature (no duplicate codes returned or saved).
- **SC-004**: 100% of customer edits preserve the existing code (no drift, no
  blanking, no regeneration).

## Assumptions

- **Numbering format**: default per-tenant prefix `CUS-` followed by a monotonic
  sequence: `CUS-0001`, `CUS-0002`, … — mirrors the existing `PUR-INV-{number}`
  convention used elsewhere in the system; final prefix/format confirmed at
  implementation and recorded in the ADR.
- **Scope boundaries**: only customer **create** becomes auto-code; the
  customers list and edit screens continue to display codes; no change to other
  entities (vendors, accounts, invoices retain their existing code/number input
  behaviour).
- **Data/environment**: code remains a required, tenant-unique DB value — the
  feature changes generation, not storage; existing customer codes are never
  migrated or altered.
- **Dependency**: requires the existing `Customer` model, `CustomerSerializer`,
  and `CustomerModal` to be reused as-is; no new app or schema migration is
  required beyond the generation behaviour.
