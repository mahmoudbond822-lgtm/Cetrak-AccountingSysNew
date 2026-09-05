# Feature Specification: Sales Cycle (Foundation)

**Feature Branch**: `009-sales-cycle`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "Build a proper Sales module that integrates tightly with the existing Accounting module. Focus on establishing the Sales foundation and the core sales transaction flow while keeping the design extensible for future Inventory, Payments, Tax/VAT, and AI features."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Customers (Priority: P1)

A business owner or accountant needs to maintain a list of the customers the company sells to. Each customer belongs to exactly one company workspace (tenant) and can never be seen or referenced from another workspace.

**Why this priority**: Customers are the base object of every sales document. Without a customer list, no invoice can be created.

**Independent Test**: An authorized user can create a customer with a code, name, and contact details, see it in the customer list, edit it, and deactivate it. A user in a different workspace cannot see, edit, or reference that customer and cannot create a customer with a duplicate code in their own workspace.

**Acceptance Scenarios**:

1. **Given** an authorized user in a workspace, **When** they create a customer with a unique code, name, and contact details, **Then** the customer is saved and appears in that workspace's customer list.
2. **Given** an existing customer, **When** an authorized user edits its name, address, or status, **Then** the changes are saved and reflected in the list.
3. **Given** an existing customer, **When** an authorized user deactivates it, **Then** the customer no longer appears in active lists but historical invoices remain intact.
4. **Given** a workspace with customer code `C-001`, **When** a user in that workspace creates another customer with code `C-001`, **Then** the creation is rejected with a duplicate-code error.
5. **Given** a user in Workspace B, **When** they look up a customer that exists in Workspace A, **Then** they receive the same result as for an unknown customer and no Workspace A data is disclosed.

---

### User Story 2 - Create and Manage Sales Invoices (Priority: P1)

An accountant creates an invoice for a customer from their own workspace, adds line items (description, quantity, unit price, per-line tax rate), and the system computes subtotal, discount, tax, and total. The invoice is stored as a draft that can be corrected until it is posted.

**Why this priority**: Invoices are the core transaction that drives revenue and the accounting integration. Quote/Order are deferred (see Assumptions) but share the same customer and document-line foundation.

**Independent Test**: An authorized user can create a draft invoice with one or more lines, review the computed subtotal, tax, and total, correct line quantities/prices, and confirm the draft appears in the invoice list with status "Draft".

**Acceptance Scenarios**:

1. **Given** an authorized user and a customer in the same workspace, **When** they create an invoice with at least one line (positive quantity, non-negative price, valid tax rate), **Then** the invoice is saved as a draft with correct subtotal, tax, and total computed as decimals.
2. **Given** a draft invoice, **When** the user edits its lines, customer, dates, or notes, **Then** the edits are allowed and totals are recomputed.
3. **Given** an invoice with a line that has zero or negative quantity, a negative price, a tax rate outside `0–100`, or a missing description, **When** the user submits it, **Then** validation fails and nothing is saved.
4. **Given** an invoice whose subtotal is fully offset by a discount (or whose total is zero or negative), **When** the user submits it, **Then** validation fails and nothing is saved.
5. **Given** a workspace with an existing invoice number, **When** a user creates another invoice with the same number, **Then** creation is rejected as a duplicate; the same number may be reused by a different workspace.
6. **Given** an invoice referencing a customer ID from another workspace, **When** the user submits it, **Then** the invoice is rejected and no partially-created invoice or line is saved.
7. **Given** a posted invoice, **When** the user attempts to modify or delete it, **Then** the request is rejected because posted invoices are immutable.

---

### User Story 3 - Post Sales Invoices to Accounting (Priority: P1)

When an accountant posts a draft invoice, the system records a single balanced accounting journal entry in the workspace's general ledger: debit Accounts Receivable, credit Sales Revenue, and credit VAT Payable (when tax applies). The mapping to these accounts is configured per workspace by an administrator; the system never hard-codes account identifiers.

**Why this priority**: Posting is the moment sales activity reaches the accounting system. It is the highest-value and highest-risk capability in this feature and must preserve every accounting invariant.

**Independent Test**: After configuring the workspace's sales accounting accounts, an authorized user posts a draft invoice and the system creates one balanced journal entry where the debit to Accounts Receivable equals the invoice total and credits equal subtotal − discount plus tax. Posting the same invoice twice is rejected, and a failed posting leaves no partial accounting or sales writes.

**Acceptance Scenarios**:

1. **Given** a fully configured workspace and a draft invoice, **When** the user posts the invoice, **Then** the invoice status becomes "Posted" and exactly one balanced journal entry is created with Dr Accounts Receivable = invoice total, Cr Sales Revenue = subtotal − discount, and Cr VAT Payable = tax (when tax > 0).
2. **Given** a posted invoice, **When** the user attempts to post it again, **Then** the request is rejected and no second journal entry is created.
3. **Given** a workspace whose sales accounting accounts are not configured, **When** the user posts an invoice, **Then** posting fails with a safe, clear error and neither the invoice status nor any journal entry is changed.
4. **Given** an invoice whose configured mapping account is inactive, invalid, or type-mismatched, **When** the user posts it, **Then** posting fails and no partial journal entry, invoice status change, or line write occurs.
5. **Given** a user in Tenant B attempting to post into a journal entry that would reference Tenant A accounts, **When** posting is attempted, **Then** it is rejected and no cross-tenant reference is ever persisted.
6. **Given** a user who lacks posting permission, **When** they call the post action, **Then** the request is forbidden.

---

### User Story 4 - Configure Sales-to-Accounting Account Mapping (Priority: P2)

An administrator configures which accounts in the workspace's chart of accounts are used when invoices are posted: Accounts Receivable (Asset), Sales Revenue (Revenue), and VAT Payable (Liability). The configuration is workspace-specific and validated so a workspace can only reference its own accounts.

**Why this priority**: Defaulting to hard-coded account IDs would fail for real charts of accounts and would corrupt ledgers. An explicit, tenant-scoped mapping keeps the integration maintainable and safe.

**Independent Test**: An administrator can read and update the mapping with accounts from their own workspace, and the system rejects any configured account from another workspace.

**Acceptance Scenarios**:

1. **Given** an administrator with accounts in the workspace, **When** they select an Accounts Receivable, Sales Revenue, and VAT Payable account and save, **Then** the mapping persists and is used by invoice posting.
2. **Given** an administrator submits a mapping referencing an account from another workspace or an account of the wrong type, **When** they save, **Then** the mapping is rejected and no partial configuration is saved.
3. **Given** a non-administrator user, **When** they attempt to read or modify the mapping, **Then** the request is forbidden.

---

### User Story 5 - View Sales Data with Role-Based Access (Priority: P2)

Team members see sales data according to the same role model used by accounting: Admin, Accountant, and Manager. Managers can view customers, invoices, and their status; only Admin and Accountant can create, edit, and post sales documents.

**Why this priority**: Role-appropriate visibility matches the existing permission conventions and avoids a new role system.

**Independent Test**: A Manager can list customers and invoices, but create and post actions are forbidden. Admin and Accountant users can create, edit, and post.

**Acceptance Scenarios**:

1. **Given** a Manager user and existing customers and invoices, **When** they list or retrieve them, **Then** the data is returned.
2. **Given** a Manager user, **When** they attempt to create or edit a customer or invoice, **Then** the request is forbidden.
3. **Given** an Accountant user, **When** they create, edit, and post an invoice, **Then** the actions succeed.
4. **Given** an unauthenticated request to any sales endpoint, **When** the request arrives, **Then** it is rejected as unauthorized.

---

### Edge Cases

- What happens when a customer code is duplicated in the same workspace? The creation must be rejected; the same code is allowed across different workspaces.
- What happens when an invoice references a customer ID from another workspace? The invoice is rejected outright with no invoice or line row created and no customer details disclosed.
- What happens when an invoice's total is zero or negative (e.g., discount equals or exceeds subtotal)? Draft creation is rejected; a zero-amount invoice could never produce a valid accounting entry.
- What happens when posting occurs while the accounting mapping is incomplete (e.g., revenue account missing)? Posting fails cleanly with no writes and a generic message.
- What happens when posting references an inactive or wrong-type account? Posting fails with no partial writes; the mapping must be corrected by an administrator.
- What happens when an invoice has zero tax? The VAT Payable line is omitted and the entry remains balanced.
- What happens when a line quantity, price, or computed total exceeds the decimal column size? Validation rejects out-of-range monetary values.
- What happens when a customer is deactivated but has invoices? Existing invoices remain intact; new invoices may reference only active customers.
- What happens when a user in another workspace knows an invoice number? Retrieval returns 404-equivalent behavior and discloses no invoice data.
- What happens if the generated journal reference collides with an existing manual journal entry during posting? Posting fails safely with a generic error and the transaction rolls back.
- What happens when due_date precedes invoice_date? The invoice is rejected unless due_date is omitted.
- What happens when a user belongs to more than one workspace? Every sales action and query uses only the currently active tenant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let authorized users create, list, retrieve, edit, and deactivate customers, with each customer scoped to exactly one tenant.
- **FR-002**: System MUST enforce unique customer codes per tenant and unique invoice numbers per tenant.
- **FR-003**: System MUST require a customer code and name and MUST allow editing of the customer's code, name, contact, address, and tax identifier while no posting constraint prevents it.
- **FR-004**: System MUST compute invoice subtotal, tax, and total using Decimal arithmetic; floating-point arithmetic is prohibited for money.
- **FR-005**: System MUST recompute stored invoice totals from line values at save time so stored amounts always match the lines.
- **FR-006**: System MUST validate invoice lines so that each line has a description, a quantity > 0, a unit price ≥ 0, and a tax rate between 0 and 100 inclusive.
- **FR-007**: System MUST validate headers so that discount ≥ 0, discount ≤ subtotal, and total > 0; at least one line is required; due_date ≥ invoice_date when due_date is provided.
- **FR-008**: System MUST enforce an invoice lifecycle where drafts can be edited and deleted, and posted invoices are immutable.
- **FR-009**: System MUST reject invoice creation that references a customer outside the user's active tenant, without partial writes and without disclosing the customer's details.
- **FR-010**: System MUST post invoices into the accounting system as a single balanced journal entry using a per-tenant, admin-configured account mapping (Accounts Receivable, Sales Revenue, VAT Payable).
- **FR-011**: System MUST prevent duplicate posting of the same invoice and MUST link each posted invoice to exactly one journal entry (idempotent posting).
- **FR-012**: System MUST persist the invoice status change and its journal entry in a single database transaction so that any failure leaves no partial writes.
- **FR-013**: System MUST reject posting when the account mapping is incomplete, references inactive accounts, or references wrong-type accounts, with safe non-disclosing errors.
- **FR-014**: System MUST reject any cross-tenant account reference in sales accounting integration, following the Feature 008 isolation pattern.
- **FR-015**: System MUST expose sales endpoints only to authenticated users and scope every query to the active tenant.
- **FR-016**: System MUST allow all existing accounting APIs and behavior to continue unchanged.

### Non-Functional Requirements *(mandatory)*

- **NFR-001**: Sales list and detail queries return within normal interactive latency following the existing accounting query patterns and indexed tenant/customer/number columns.
- **NFR-002**: Invoice posting performs a bounded number of writes inside a single transaction; no unbounded loops or N+1 queries.
- **NFR-003**: All sales source code follows the existing project structure (models → services → serializers/views) and conventions; no fat views.
- **NFR-004**: No new third-party dependencies are introduced.
- **NFR-005**: The sales module is designed so future Quote, Order, Payment, Inventory, Tax configuration, and AI features can be added without breaking Sales Invoice APIs.

### Security Requirements *(mandatory)*

- **SEC-001**: Every sales model MUST carry a tenant reference and every query MUST filter by the active tenant (Constitution Article I).
- **SEC-002**: Cross-tenant references (customer in invoice, accounts in settings) MUST be rejected at the serializer boundary before any write (Feature 008 pattern).
- **SEC-003**: Failed or rejected operations MUST NOT leave partial writes — invoice rows, lines, journal entries, or configuration.
- **SEC-004**: Error responses MUST NOT disclose other tenants' customer codes/names/contact data, invoice numbers, account names/types, or record existence. Unknown, cross-tenant, and invalid references MUST be indistinguishable.
- **SEC-005**: Posting MUST NOT accept, resolve, or persist any account that is not owned by the active tenant.
- **SEC-006**: Posting MUST be idempotent — a concurrent or repeated post never creates more than one journal entry per invoice.
- **SEC-007**: Role enforcement MUST reject forbidden actions (Manager create/post, non-admin settings) with 403 before any business logic runs.

### Accounting Integration *(mandatory)*

When a draft invoice is posted, the system creates exactly one journal entry with the following lines:

- **Dr** `Accounts Receivable` = invoice `total`
- **Cr** `Sales Revenue` = invoice `subtotal` − invoice `discount`
- **Cr** `VAT Payable` = invoice `tax` (omitted when tax is zero)

Balance holds by construction because `total = (subtotal − discount) + tax`. Requirements:

- The accounts used come from the workspace's `Sales Accounting Settings`; the system never hard-codes account IDs.
- The entry uses the invoice date, a tenant-unique reference (`SALES-INV-{number}`), and is created already posted.
- The invoice is linked to the created entry (exactly one entry per invoice).
- Any failure in the mapping, account validity, or write raises before commit; the transaction rolls back everything.

### Key Entities *(include if feature involves data)*

- **Customer**: A tenant-owned party to whom the workspace sells. Has a tenant-scoped unique code, name, contact and address details, optional tax identifier, and active status.
- **Sales Invoice**: A tenant-owned sales document with a unique number, customer, dates, notes, discount, and computed subtotal, tax, and total. Lifecycle: Draft → Posted.
- **Sales Invoice Line**: A line on an invoice with description, quantity, unit price, tax rate, and computed line totals.
- **Sales Accounting Settings**: A tenant-owned configuration mapping invoice posting to the workspace's Accounts Receivable, Sales Revenue, and VAT Payable accounts. Never stores hard-coded account IDs.

### Data Model *(mandatory - see data-model.md)*

Four new tenant-scoped models in the sales app: `SalesAccountingSettings` (per-tenant singleton mapping), `Customer`, `SalesInvoice` (Draft/Posted lifecycle, unique number per tenant, decimal money), `SalesInvoiceLine` (description, quantity, unit price, tax rate, computed line totals). All money uses `DecimalField(max_digits=19, decimal_places=4)`. Details and constraints: [data-model.md](data-model.md).

### API Requirements *(mandatory - see contracts/sales-api.md)*

RESTful endpoints under `/api/v1/sales/` following the accounting conventions: `customers` (list/create/retrieve/patch), `invoices` (list/create/retrieve/patch for drafts, `POST invoices/{id}/post/`), `settings` (GET/PUT, Admin only). Every endpoint requires authentication and an active tenant context; errors use the standard DRF JSON shape. Details: [contracts/sales-api.md](contracts/sales-api.md).

### UI Requirements *(mandatory)*

- Sales pages reuse the existing Cetrak design system: same page/nav/table/form/notification patterns, CSS variables, and service-layer module (`salesService.js` mirroring `accountingService.js`).
- Views: customers list with create/edit, invoices list with status and draft edit, invoice form with dynamic line rows, invoice detail/post action, and Admin-only settings page for the account mapping.
- Role-gated controls: Manager sees read-only views; create/edit/post buttons appear only for Admin/Accountant; settings only for Admin.
- No new visual language or design framework.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tested customer reads, creates, updates, and deactivations complete correctly within the active tenant, and 0% of cross-tenant customer requests succeed.
- **SC-002**: 100% of tested invoice posts produce exactly one balanced journal entry where Dr AR = invoice total and Cr Revenue + Cr VAT = the same total.
- **SC-003**: 100% of duplicate posting attempts are rejected without creating a second journal entry or changing any balance.
- **SC-004**: 100% of posting failures (missing mapping, inactive/wrong-type accounts, cross-tenant references) leave invoice status, journal entries, and all balances unchanged (no partial writes).
- **SC-005**: 100% of tested invalid invoice inputs (zero/negative quantity, negative price, tax rate outside 0–100, discount ≥ subtotal, zero/negative total, cross-tenant customer) are rejected before any write.
- **SC-006**: 100% of existing backend tests (accounting, accounts) continue to pass after this feature.
- **SC-007**: Error messages for inaccessible (unknown, cross-tenant, or invalid) sales references disclose 0 other-tenant details (customer codes/names, invoice numbers, account data, or existence).

## Test Strategy *(mandatory)*

- **Backend (pytest / Django test runner)** in `backend/apps/sales/tests/test_sales_api.py`, following the existing `APITestCase` + tenant-header helper pattern:
  - Customer CRUD, code uniqueness, tenant isolation, cross-tenant 404-equivalence, permission matrix (unauth/Manager/Accountant/Admin).
  - Invoice creation, validation failures, decimal calculations, number uniqueness, cross-tenant customer rejection with no partial writes, draft edit, posted immutability.
  - Posting: success with balanced entry, zero-tax, discount, duplicate-post rejection, incomplete mapping, inactive/wrong-type account rollback, journal reference collision, cross-tenant protection, permission matrix.
  - Settings: get/put, cross-tenant and wrong-type account rejection, Admin-only.
- **Regression**: full `apps/accounts/tests/` + `apps/accounting/tests/` + `apps/sales/tests/` run — all pass.
- **Frontend**: no automated test framework exists in the project; verification is a successful production build (`npm run build`) and lint.

## Assumptions

- Sales Quote and Sales Order are explicitly deferred to a future feature. The customer and invoice data model is designed so they can be added without breaking Sales Invoice APIs.
- Payments/receipts, Inventory, and dedicated Tax/VAT configuration are deferred. The VAT Payable accounting line is derived from the per-line tax rate; full tax configuration and payment posting are future features.
- The system is single-currency for this feature; no currency field is introduced because the existing accounting architecture has none. Multi-currency is a future concern.
- Invoice numbers are user-supplied at creation and enforced unique per tenant, matching the existing Journal Entry reference convention. Auto-numbering is a future enhancement.
- Deactivated customers may remain referenceable by existing invoices; new invoices may reference only active customers.
- The sales accounting mapping must be configured per workspace before posting; the system does not auto-provision accounts.
- No new roles are introduced; the existing Admin/Accountant/Manager roles are reused.
- Deployment, billing, and AI features remain out of scope per the project constitution and milestone plan.