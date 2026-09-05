# Feature Specification: Payments & Receipts

**Feature Branch**: `010-payments-and-receipts`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "Payments & Receipts — collect payments from customers against posted sales invoices. A payment reduces the customer's accounts receivable by posting a balanced Journal Entry (Dr Cash/Bank, Cr Accounts Receivable)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Post a payment to a posted sales invoice (Priority: P1)

An accountant opens a customer's posted sales invoice and records a payment for the invoiced amount. The system stores the payment and posts a single balanced Journal Entry (Dr Cash/Bank, Cr Accounts Receivable) using the tenant's configured accounts. The payment cannot be posted twice.

**Why this priority**: This is the core value of the feature — recording money received against a sale and reducing the receivable on the books. Without it there is no feature.

**Independent Test**: Can be fully tested by creating and posting a sales invoice, then creating and posting one payment equal to the invoice total, and verifying (a) a Journal Entry exists with Dr Cash/Bank = amount, Cr Accounts Receivable = amount, (b) the invoice shows zero outstanding balance.

**Acceptance Scenarios**:

1. **Given** a posted sales invoice of 10,000 and configured sales accounting settings, **When** an accountant posts a payment of 10,000 against it, **Then** a single balanced Journal Entry is created that debits the selected cash/bank account 10,000 and credits the configured Accounts Receivable account 10,000, and the invoice's outstanding balance becomes 0.
2. **Given** the same scenario, **When** the accountant attempts to post the same payment a second time, **Then** the system rejects it with an error ("payment already posted") and does not create a second Journal Entry.
3. **Given** sales accounting settings **missing** the Accounts Receivable account, **When** the accountant posts a payment, **Then** the system rejects the posting with a clear configuration error and creates no Journal Entry.
4. **Given** a **draft** sales invoice (not yet posted), **When** the accountant records a payment against it, **Then** the system rejects it and does not create any payment or Journal Entry.

---

### User Story 2 - Partial and multiple payments with outstanding balance (Priority: P1)

Customers settle invoices in instalments. An invoice of 10,000 receives a first payment of 4,000 and later a second of 6,000. After each payment the invoice shows its remaining (outstanding) balance. A payment that exceeds the outstanding balance is rejected so the receivable can never go negative.

**Why this priority**: Partial and multiple payments are the most common real-world settlement pattern and drive the outstanding-balance and overpayment protection rules.

**Independent Test**: Can be fully tested by posting an invoice of 10,000, posting 4,000 against it (outstanding becomes 6,000), posting 6,000 against it (outstanding becomes 0), then verifying a third payment of 1 exceeds the outstanding and is rejected.

**Acceptance Scenarios**:

1. **Given** a posted invoice of 10,000 and a posted payment of 4,000, **When** the invoice's outstanding balance is read, **Then** it equals 6,000.
2. **Given** the same state, **When** a second payment of 6,000 is posted, **Then** it succeeds and the outstanding balance becomes 0.
3. **Given** a posted invoice of 10,000 with no payments, **When** a payment of 10,001 is created/posted, **Then** the system rejects it ("amount exceeds the outstanding balance") and no Journal Entry is created.
4. **Given** a posted invoice of 10,000 with a posted payment of 4,000, **When** a payment of 6,001 is attempted, **Then** the system rejects it.

---

### User Story 3 - Manage draft payments before posting (Priority: P2)

Payments are recorded as drafts first. An accountant can fix mistakes (amount, date, method, cash/bank account, reference, notes) and delete drafts that are no longer needed. Only after confirmation is a payment posted and booked to the ledger; a posted payment can never be edited or deleted.

**Why this priority**: Draft-then-post matches the established invoice workflow and prevents erroneous postings. Guardrails on posted payments protect ledger integrity.

**Independent Test**: Can be fully tested by creating a draft payment, editing it, deleting a different draft, and verifying a posted payment cannot be edited or deleted.

**Acceptance Scenarios**:

1. **Given** a draft payment of 4,000, **When** its amount is edited to 3,500, **Then** the change is persisted and the payment remains a draft with no Journal Entry.
2. **Given** a draft payment, **When** it is deleted, **Then** it is removed and no Journal Entry is ever created.
3. **Given** a posted payment, **When** an edit or delete is attempted, **Then** the system rejects it ("only draft payments can be edited/deleted").

---

### User Story 4 - Track payments and outstanding balances in the UI (Priority: P3)

The accountant sees a Payments screen listing every payment (number, customer, invoice, date, method, amount, status), the outstanding balance of each invoice, and can create, edit, and post payments from forms following the existing sales UI.

**Why this priority**: Delivers the feature to end users; depends on the backend (US1–US3).

**Independent Test**: Can be fully tested by opening the Payments page, seeing posted invoices with outstanding amounts, creating a draft payment through the form, and posting it via the confirmation dialog.

**Acceptance Scenarios**:

1. **Given** a posted invoice with outstanding balance 6,000, **When** the Payments page is opened, **Then** the invoice is listed with its outstanding balance and a way to record a payment.
2. **Given** a draft payment form, **When** an amount larger than the outstanding balance is entered, **Then** the form shows a validation error before submission.

---

### Edge Cases

- Payment posted against an invoice in **another tenant** — rejected ("Invoice not found.") with no information disclosure.
- Cash/bank account supplied that belongs to **another tenant**, is **inactive**, or is **not an Asset** type — rejected at validation, no Journal Entry.
- **Two concurrent postings** for the same invoice attempting to use the same remaining balance — the second must fail; posting locks the invoice row so the outstanding check and Journal Entry are atomic.
- Amount of zero or negative — rejected.
- Payment date in the past/future — accepted (no constraint) unless the date is missing (required).
- Duplicate payment number within the same tenant — rejected ("Payment number already exists.").
- Duplicate Journal Entry reference (same invoice + same payment number) — rejected inside the transaction.
- Payment against an invoice that is fully paid — rejected with outstanding-balance error.
- Missing Accounts Receivable configuration — posting fails with a configuration error; drafts can still be saved.
- VAT/sales revenue account missing — does **not** block payment posting (only the Accounts Receivable account matters for payments).
- Deleted-then-recreated payment reusing a number — allowed only if the number is no longer in use (unique per tenant is ambivalent of history).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a user with the sales manage permission to create a **draft payment** against a **posted** sales invoice.
- **FR-002**: A payment MUST reference exactly one sales invoice; the invoice MUST belong to the caller's tenant.
- **FR-003**: A payment MUST record `number`, `payment_date`, `amount`, `payment_method`, and a `cash_account` (an active tenant-scoped `Asset` account).
- **FR-004**: Payment number MUST be unique per tenant; duplicates MUST be rejected.
- **FR-005**: System MUST reject a payment amount that is zero, negative, or greater than the invoice's current outstanding balance (**overpayment prevention**).
- **FR-006**: Outstanding balance MUST be computed as `invoice.total - sum(amount of all posted payments for that invoice)`.
- **FR-007**: Only a **posted** invoice MAY receive payments; draft invoices MUST be rejected.
- **FR-008**: Only **draft** payments MAY be edited or deleted; posted payments MUST be immutable (edit/delete rejected).
- **FR-009**: System MUST support posting a draft payment, which:
  - MUST create exactly one balanced Journal Entry referencing the tenant's configured Accounts Receivable account (from Sales Settings) with `Dr cash_account = amount`, `Cr accounts_receivable = amount`;
  - MUST transition the payment to `Posted`;
  - MUST be idempotent — posting an already-posted payment MUST fail with a clear error and MUST NOT create a second Journal Entry.
- **FR-010**: Payment posting MUST be atomic with the outstanding-balance check (row lock) so concurrent postings cannot both use the same balance.
- **FR-011**: If the tenant's Sales Settings lack an **active**, tenant-scoped Accounts Receivable account, payment posting MUST fail with a configuration error; draft creation MUST still be allowed.
- **FR-012**: The Journal Entry reference for a payment MUST be `PAY-INV-{invoice.number}-{payment.number}` and MUST respect the existing unique-reference-per-tenant constraint.
- **FR-013**: A payment's `cash_account` MUST be tenant-scoped, active, and of type `Asset`.
- **FR-014**: System MUST expose for each sales invoice its `paid_amount` and `outstanding_balance` (read-only) so clients can display remaining balance.
- **FR-015**: Payment read/list endpoints MUST expose the payment's `invoice`, `customer`, `status`, `journal_entry` (when posted), and computed outstanding of the invoice.
- **FR-016**: All payment records and Journal Entries MUST be tenant-isolated; cross-tenant references MUST be rejected without error detail.
- **FR-017**: Permission gating MUST reuse the existing sales permissions (`CanViewSales` read, `CanManageSales` create/edit/delete, `CanPostSalesInvoice` post); no new permission models.
- **FR-018**: Payment reversal/cancellation for posted payments is **out of scope** for this feature; the documented correction path is a manual reversing Journal Entry. Drafts can be deleted before posting.

### Key Entities *(include if feature involves data)*

- **Payment**: represents money received from a customer against a single posted sales invoice. Attributes: `number`, `invoice` (FK), `payment_date`, `amount`, `method` (Cash / Bank Transfer / Card / Check), `cash_account` (FK to accounting Account, Asset type), `reference` (external, optional), `notes` (optional), `status` (Draft/Posted), `journal_entry` (OneToOne to accounting JournalEntry, set on posting), `posted_at`.
- **PaymentStatus**: enum `Draft` → `Posted`; Draft is editable/deletable, Posted is immutable (no reversal in this feature).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An accountant can record and post a payment against a posted sales invoice through the API in one request round-trip (create draft then post), with the ledger updated atomically.
- **SC-002**: Outstanding balance for an invoice with partial/multiple payments always equals `total - sum(posted payments)` and is consistent across the invoice list, the payment list, and the payment form.
- **SC-003**: Zero overpayment postings reach the ledger — every attempt to post more than the outstanding balance is rejected.
- **SC-004**: No double-posting reaches the ledger — re-posting the same payment idempotently fails.
- **SC-005**: Every payment posting produces exactly one balanced Journal Entry; sum of debits equals sum of credits.
- **SC-006**: No cross-tenant data leak — payments, invoices, and accounts from other tenants are never returned or referenced.

## Assumptions

- **Assumption**: Payments are single-currency; the tenant posts in one currency (existing system assumption — no currency field is added).
- **Assumption**: Payment numbers are **user-supplied and unique per tenant**, mirroring invoice numbering; automatic sequential numbering is a future enhancement.
- **Assumption**: Each payment targets exactly one invoice (no bulk allocation across multiple invoices in v1).
- **Assumption**: Each payment uses exactly one cash/bank account (a single Dr line); split payments across multiple accounts are future work.
- **Assumption**: Reversal of posted payments is deferred; the correction path is a manual reversing Journal Entry (FR-018).
- **Assumption**: Payment method choices are a fixed enum (Cash, Bank Transfer, Card, Check); free-form method configuration is future work.
- **Assumption**: The Accounts Receivable account is taken from the tenant's existing Sales Settings. No new settings fields are added.
- **Assumption**: The existing sales permission set is reused; no new groups or permissions are introduced.
- **Assumption**: The backend is the source of truth; the UI (US4) only presents backend-computed balances and validation.
- **Dependency**: Requires Feature 009 (sales invoices + posting) and the accounting core (accounts, journal entries).