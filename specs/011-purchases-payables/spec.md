# Feature Specification: Purchases & Accounts Payable

**Feature Branch**: `011-purchases-payables`

**Created**: 2026-09-05

**Status**: Draft (awaiting review)

**Input**: User description: "Purchases & Accounts Payable — record vendor purchases against an AP workflow that integrates directly with the Accounting system. Vendor → Purchase Invoice → Accounts Payable → Payment → Journal Entry. This is the purchasing-side equivalent of Features 009 + 010, following the existing architecture rather than duplicating code."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage vendors (Priority: P1)

An accountant records a vendor (code, name, contact info, address, tax identifier). Vendor codes are unique within the tenant; a vendor cannot be deleted once it has purchase invoices (deactivate instead). Cross-tenant vendors are impossible.

**Why this priority**: Vendors are the foundation of the purchasing domain — no purchase invoice can exist without a vendor, mirroring customers.

**Independent Test**: Can be fully tested by creating a vendor, editing it, attempting a duplicate code, attempting to delete a vendor with invoices, and attempting tenant-B access to a tenant-A vendor.

**Acceptance Scenarios**:

1. **Given** an Admin/Accountant role, **When** a vendor is created with a unique code, **Then** it is stored and returned with `is_active=true`, and a second vendor with the same tenant/code is rejected.
2. **Given** a vendor with purchase invoices, **When** delete is attempted, **Then** the system rejects it (`400`, "Vendor has purchase invoices and cannot be deleted. Deactivate instead.") and forbids hard deletion; a vendor without invoices is deactivated (`204`, `is_active=false`). This mirrors the Feature 009 customer behavior.
3. **Given** tenant B, **When** tenant A's vendor id is requested, **Then** `404` with a generic error (no disclosure).

---

### User Story 2 - Create and post a purchase invoice (Priority: P1)

An accountant creates a purchase invoice for an active vendor with line items. Totals (subtotal, discount, tax, total) are computed as `Decimal(19,4)` exactly like sales invoices. Posting books a single balanced Journal Entry — **Dr Expense, Dr Input VAT, Cr Accounts Payable** — using the tenant's configured purchase accounts; posting is idempotent and can never run for a cross-tenant vendor or account.

**Why this priority**: This is the core value of the feature — the purchasing-side accounting event that creates the AP balance.

**Independent Test**: Can be fully tested by creating and posting a 11,500 purchase invoice (10,000 net + 1,500 VAT) and verifying one balanced JE with Dr Expense 10,000, Dr Input VAT 1,500, Cr Accounts Payable 11,500.

**Acceptance Scenarios**:

1. **Given** configured purchase accounting settings (AP=Liability, Expense=Expense, Input VAT=Asset), **When** a draft purchase invoice with lines (net 10,000, VAT 1,500) is posted, **Then** one balanced Journal Entry is created: Dr Expense 10,000, Dr Input VAT 1,500, Cr Accounts Payable 11,500, and the invoice becomes `Posted`.
2. **Given** the same invoice, **When** posting is attempted a second time, **Then** it is rejected ("Only draft purchase invoices can be posted.") and no second Journal Entry exists.
3. **Given** purchase settings missing the Accounts Payable account, **When** posting is attempted, **Then** it fails with a configuration error and no Journal Entry is created.
4. **Given** a draft purchase invoice, **When** it is edited, **Then** number, vendor, dates, and lines can change and totals are recomputed.
5. **Given** a **posted** purchase invoice, **When** edit/delete is attempted, **Then** it is rejected (immutable after posting).

---

### User Story 3 - Partial and multiple payments with outstanding AP (Priority: P1)

Vendors are settled in instalments. A purchase invoice of 20,000 receives a first payment of 7,000 (outstanding AP 13,000) and a second of 13,000 (outstanding AP 0). A payment exceeding the outstanding AP is rejected so Accounts Payable can never go negative.

**Why this priority**: Partial/multiple settlement is the normal AP workflow and drives the outstanding-balance and overpayment-protection rules (directly mirroring Feature 010).

**Independent Test**: Can be fully tested by posting an invoice of 20,000, paying 7,000 (outstanding 13,000) and 13,000 (outstanding 0), then rejecting a third payment of 1.

**Acceptance Scenarios**:

1. **Given** a posted purchase invoice of 20,000, **When** a payment of 7,000 is posted, **Then** the invoice reports `paid_amount: "7000.0000"` and `outstanding_balance: "13000.0000"`.
2. **Given** the same state, **When** a second payment of 13,000 is posted, **Then** outstanding becomes `0.0000`.
3. **Given** a posted purchase invoice of 20,000 with no payments, **When** a payment of 20,001 is created or posted, **Then** it is rejected ("Amount exceeds the outstanding balance.") and no Journal Entry exists.
4. **Given** a **draft** purchase invoice, **When** a payment is attempted against it, **Then** it is rejected ("Only posted purchase invoices can be paid.").

---

### User Story 4 - Payment posting books the correct AP entry (Priority: P1)

Paying a vendor reduces the payable and the cash balance: posting a draft payment books **Dr Accounts Payable, Cr Cash/Bank** (the reverse of a customer receipt), with AP taken from the tenant's configured purchase accounts. Draft payments are editable/deletable; posted payments are immutable and idempotent.

**Why this priority**: Correct accounting semantics for the AP side are the point of the feature — money going out to a vendor reduces both AP and cash.

**Independent Test**: Can be fully tested by posting a purchase invoice, posting a full payment, and verifying the JE is Dr AP = amount, Cr cash = amount and balanced.

**Acceptance Scenarios**:

1. **Given** a posted purchase invoice of 20,000, **When** a draft payment of 20,000 is posted, **Then** a single balanced Journal Entry is created with Dr Accounts Payable 20,000, Cr Cash/Bank 20,000, and the invoice shows outstanding `0.0000`.
2. **Given** an already-posted payment, **When** posting is attempted again, **Then** it is rejected and no second Journal Entry exists.
3. **Given** a posted payment, **When** edit or delete is attempted, **Then** it is rejected ("Only draft payments can be edited/deleted.").

---

### User Story 5 - Track purchases and payables in the UI (Priority: P3)

The accountant sees a Purchases UI (Vendors, Purchase Invoices, Payments, Settings) following the existing Cetrak design system, including VAT line-item totals and outstanding AP displayed before payment.

**Why this priority**: Delivers the feature to end users; depends on the backend (US1–US4).

**Independent Test**: Can be fully tested by opening the Purchase Invoices page, creating/posting an invoice, opening the Payments page and recording a payment against a posted invoice with its outstanding shown.

**Acceptance Scenarios**:

1. **Given** a posted purchase invoice with outstanding AP 13,000, **When** the payments page is opened, **Then** the invoice is listed with its outstanding balance and a form to record a payment.
2. **Given** a payment form, **When** an amount larger than outstanding AP is entered, **Then** the form shows a validation error before submission (server remains authoritative).

---

### Edge Cases

- Vendor from another tenant → `"Vendor not found."` (no disclosure).
- Purchase invoice from another tenant → `"Invoice not found."`.
- Purchase invoice referencing a **cross-tenant vendor** → rejected at create/edit.
- Purchase invoice referencing a **cross-tenant account** in settings → posting fails with generic config error.
- Payment applied to another tenant's purchase invoice → `"Invoice not found."`.
- **Two concurrent payment postings** against the same invoice → the second fails because posting locks the invoice row (outstanding = 0), the same pattern as Feature 010.
- **Two concurrent invoice postings** of the same draft → one wins via the unique `(tenant, reference)` constraint; the loser gets "Journal entry reference already exists." and no partial state.
- Amount zero/negative → rejected.
- Overpayment at create (serializer) and at post (row-locked service check) → always rejected, no orphan JE.
- Duplicate invoice number within tenant → rejected.
- Missing/inactive/foreign AP, Expense, or Input VAT account at posting → configuration error; drafts and payment drafts still work.
- Invoice with `tax > 0` but **no Input VAT account configured** → posting refused (balanced-JE invariant), unlike sales' optional-VAT path.
- Vendor with inactive status → cannot be referenced by new/edited purchase invoices.
- Payment direction mixing: a Receivable payment can never be posted against a purchase invoice and vice versa (DB check constraint).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A user with the purchases manage permission MUST be able to create, edit, and deactivate **Vendors**; a vendor MUST have `tenant`, `code` (unique per tenant), `name`, contact information, `address`, `tax_id`, `is_active`, and timestamps.
- **FR-002**: A vendor with purchase invoices MUST NOT be hard-deleted; delete returns `400` with a message advising deactivation, and a vendor without invoices is deactivated (`204`) — mirroring customers.
- **FR-003**: Users MUST be able to create **draft** and **posted** **Purchase Invoices** (adopting Draft → Posted semantics from sales).
- **FR-004**: Invoice fields MUST include `number` (unique per tenant), `vendor`, `invoice_date`, `due_date`, `status`, `notes`, `discount`, `subtotal`, `tax`, `total`, `posted_at`, `posted_journal`, and derived `paid_amount`/`outstanding_balance`.
- **FR-005**: Lines MUST support `description`, `quantity`, `unit_price`, `tax_rate`, with computed `subtotal`, `tax`, `total` in `Decimal(19,4)`; floating-point money is prohibited; math reuses the sales `compute_line_totals` recipe.
- **FR-006**: `total = subtotal − discount + tax`; `quantity > 0`, `unit_price ≥ 0`, `0 ≤ tax_rate ≤ 100`, `0 ≤ discount ≤ subtotal`, `total > 0`; due date ≥ invoice date.
- **FR-007**: Only **draft** purchase invoices MAY be edited or deleted; **posted** purchase invoices MUST be immutable.
- **FR-008**: Posting a draft purchase invoice MUST:
  - validate the tenant's configured purchase accounts (AP = Liability, Expense = Expense, Input VAT = Asset; active; tenant-owned);
  - MANDATE an Input VAT account when `tax > 0` (balanced-JE invariant);
  - create exactly one balanced Journal Entry `PUR-INV-{number}` (Dr Expense net, Dr Input VAT tax, Cr AP total);
  - mark the invoice `Posted` and set `posted_journal`/`posted_at`;
  - be **idempotent** — a second posting MUST fail without creating a second entry.
- **FR-009**: Outstanding AP MUST be computed as `total − Σ posted payable payments`; overpayment MUST always be rejected (at create and at post, row-locked).
- **FR-010**: Payment posting for purchases MUST book `Dr Accounts Payable, Cr Cash/Bank` (AP from the tenant's purchase settings; `cash_account` tenant-scoped active Asset), be atomic with the outstanding check via `select_for_update` on the purchase invoice row, and be idempotent.
- **FR-011**: Payment records MUST be shared with Feature 010 via a generalized `Payment` model (`direction = Receivable | Payable`, exactly one invoice reference per payment enforced by a DB check), preserving the existing sales payments API unchanged.
- **FR-012**: Journal Entry references MUST be `PUR-INV-{purchase.number}` (invoice) and `PAY-PUR-{purchase.number}-{payment.number}` (payment), both unique per tenant.
- **FR-013**: Purchase account mapping MUST be stored in a new `PurchaseSettings` (single row per tenant: `accounts_payable`, `expense_account`, `input_vat`), mirroring `SalesSettings`; no changes to `SalesSettings` or `apps/accounting`.
- **FR-014**: All queries MUST be tenant-scoped (`.for_tenant(request.tenant_id)`); cross-tenant vendors/invoices/accounts MUST produce generic errors with no information disclosure.
- **FR-015**: No hard-coded account or tenant IDs anywhere; no `float` in any money path.
- **FR-016**: Permissions MUST reuse the existing role system with purchases analogues: `CanViewPurchases`, `CanManagePurchases`, `CanPostPurchaseInvoice`, `CanConfigurePurchases`; no new roles.
- **FR-017**: APIs MUST follow the existing versioned routing and DRF conventions: vendors, purchase invoices (+ lines), posting action, payments, settings under `api/v1/purchases/`.
- **FR-018**: Purchase invoice cancellation/voiding and payment reversal are **out of scope**; the documented correction path is a manual reversing Journal Entry, and cancelled state is deferred (matches the sales/payments architecture).

### Key Entities

- **Vendor**: tenant, `code` (unique/tenant), `name`, `email`, `phone`, `address`, `tax_id`, `is_active`, timestamps.
- **PurchaseInvoice**: tenant, `number` (unique/tenant), `vendor` FK PROTECT, `invoice_date`, `due_date`, `status` (Draft/Posted), `notes`, `discount`/`subtotal`/`tax`/`total` Decimal(19,4), `posted_at`, `posted_journal` OneToOne PROTECT.
- **PurchaseInvoiceLine**: `invoice` FK CASCADE, `description`, `quantity`, `unit_price`, `tax_rate`, computed `subtotal`/`tax`/`total`.
- **Payment** (generalized, in `apps/sales`): existing receipt columns plus `direction` (Receivable/Payable) and `purchase_invoice` FK with a check constraint ensuring exactly one invoice reference.
- **PurchaseSettings**: tenant (unique), `accounts_payable` (Liability), `expense_account` (Expense), `input_vat` (Asset).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vendor CRUD round-trip works; duplicate tenant/code rejected; vendor with invoices rejects delete (`400`), vendor without invoices deactivates.
- **SC-002**: A purchase invoice can be created, edited as a draft, and posted; posting produces exactly one balanced Journal Entry (`PUR-INV-{number}`) that respects the tenant's configured accounts.
- **SC-003**: Outstanding AP always equals `total − Σ posted payable payments`; partial/full/multiple payment examples (20,000 → 7,000 → 13,000) pass; overpayment never reaches the ledger.
- **SC-004**: Every payment posting (both directions) produces exactly one balanced Journal Entry and is idempotent; concurrency is handled by row-locking.
- **SC-005**: Zero cross-tenant leakage across vendors, invoices, payments, and accounts — the Feature 010 tenant-isolation test pattern passes for purchases.
- **SC-006**: Feature 009 and Feature 010 behavior is unchanged: the full 153-test regression suite remains green.

## Assumptions

- **Currency**: single-currency system (existing assumption) — no currency field is added.
- **Item/product reference**: no product catalog exists yet; purchase lines use free-text `description` (item IDs arrive with Feature 012 Inventory). Documented as future work.
- **Single line/account mapping**: all lines post to one configured expense account (inventory/COGS splitting arrives with Feature 012).
- **Numbering**: user-supplied invoice/payment numbers unique per tenant (mirrors sales; auto-sequencing deferred).
- **Status**: Draft/Posted only for purchase invoices (mirror sales); `Cancelled`/`Void` is deferred — a "cancelled invoice cannot be paid" rule is satisfied because only Posted invoices can receive payments.
- **Payment model**: Feature 010's `Payment` is generalized with a `direction` field rather than duplicating a purchases-specific payment implementation; the sales payments API is unchanged.
- **Settings**: a new `PurchaseSettings` mirrors `SalesSettings`; SalesSettings and the accounting schema are untouched.
- **Dependency**: Requires Feature 009 (sales posting pattern), Feature 010 (payment pattern being generalized), and the accounting core. `apps.purchases` is already registered in `INSTALLED_APPS` (empty scaffold).