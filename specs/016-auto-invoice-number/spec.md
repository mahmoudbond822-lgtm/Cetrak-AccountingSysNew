# Feature Specification: Auto Invoice Number

**Feature Branch**: `016-auto-invoice-number`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Apply what we do with "customer code and vendor code " to Invoice number"

## Clarifications

### Session 2026-09-16

- Q: Should sales and purchase invoices share one numbering sequence or have independent per-type sequences? → A: Per-type — sales and purchase each run INV-0001, INV-0002 independently.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create an invoice with an auto-generated number (Priority: P1)

An accountant opens the sales or purchase invoices list → Create Invoice. The dialog shows a Number field that is visible but not editable (disabled/read-only) with a preview value for the next number (`INV-0001` for the first invoice of the business). The user fills in the customer/vendor, dates, and lines, saves, and the new invoice appears in the list with that number. Opening Create again shows the next number (`INV-0002`), incrementing by 1 for every saved invoice. Both sales and purchase invoices share this behavior, with independent per-type sequences: sales invoices run `INV-0001`, `INV-0002`, … and purchase invoices run their own `INV-0001`, `INV-0002`, … (the same number may exist once as a sale and once as a purchase — they are different documents).

**Why this priority**: This mirrors the customer/vendor pain — creation currently fails with "Invoice number is required" when no number is typed. Showing an auto, non-editable number removes the blocker and is the whole value of the request.

**Independent Test**: Can be fully tested by opening the create dialog (number visible, not editable), saving a valid invoice, and confirming the saved invoice carries the shown number.

**Acceptance Scenarios**:

1. **Given** an empty invoice list, **When** the user opens Create Invoice, **Then** the Number field is visible, disabled, and shows `INV-0001`.
2. **Given** the create dialog with the shown number, **When** the user saves a valid invoice, **Then** creation succeeds with no "number required" error and the saved invoice has exactly the shown number.
3. **Given** one saved invoice, **When** the user opens Create Invoice again, **Then** the Number field shows the next value (+1).

### User Story 2 - Numbers increment by 1 per saved invoice (Priority: P2)

Each time an invoice is saved, the system automatically increments the number by 1 from the highest existing number for that business. This ensures sequential, gap-free numbering within each business.

**Why this priority**: Guarantees that every new invoice gets a unique, incrementing number without manual entry, eliminating the "number required" error entirely.

**Independent Test**: Can be fully tested by creating several invoices in a row and confirming every number increments by exactly 1 from the previous.

**Acceptance Scenarios**:

1. **Given** one saved invoice, **When** the user saves a second invoice, **Then** the second invoice gets the next sequential number.
2. **Given** gaps from previously deleted draft invoices, **When** a new invoice is saved, **Then** the number assigns the next free sequential value (gaps are not reused).

### User Story 3 - Number is locked after creation (Priority: P3)

Once an invoice exists, its number is shown but can never be edited — not while a draft, not after posting — mirroring the customer/vendor code rule. This protects posted financial records and their journal references.

**Why this priority**: Protects posted financial records and their journal references. Lower priority than creation because it only guards existing records.

**Independent Test**: Can be fully tested by editing an existing draft invoice's lines and confirming the number is unchanged and not editable.

**Acceptance Scenarios**:

1. **Given** an existing invoice (draft or posted), **When** a user edits its lines or dates and saves, **Then** the number is unchanged.
2. **Given** the edit dialog, **When** viewed, **Then** the Number field is visible but not editable.

---

### Edge Cases

- First invoice in a new business shows the first number of the sequence.
- Numbers with gaps from deleted drafts are not reused; numbering keeps moving forward.
- Blank, whitespace, or missing number values submitted at creation are treated the same: the system assigns the next number.
- Two businesses creating their first invoices at the same time each get their own independent sequence.
- Rapid successive saves in one business never produce the same number twice.
- Opening the dialog never consumes a number: cancelled or abandoned creates leave the sequence untouched, and a stale preview is resolved at save time with the next free number plus a note.
- Explicitly supplied numbers keep current behavior: an unused explicit number is honored; an explicit number that duplicates an existing invoice of the same type in the same business is rejected as today ("Invoice number already exists").
- Journal references embed the invoice number at posting time (`SALES-INV-{number}`, `PUR-INV-{number}`) and are unaffected except for carrying the minted value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a sales or purchase invoice without the user typing a number (both invoice types are in scope).
- **FR-002**: The create-invoice dialog MUST display a Number field that is visible but not editable (disabled/read-only).
- **FR-003**: The displayed number MUST start at `INV-0001` for the first invoice of its type and increment by 1 (`INV-0002`, `INV-0003`, …) for each subsequently saved invoice of that type. Sales and purchase invoices have independent per-type sequences within each business.
- **FR-004**: System MUST assign the number authoritatively at save time and MUST NOT reject the save with a "number required" error. The dialog preview is a non-binding hint: if the previewed value was taken before save, the save MUST still succeed with the next free number and show the user the assigned number.
- **FR-005**: Every assigned number MUST be unique within the business for its invoice type; the system MUST skip values that would collide.
- **FR-006**: On edit, the system MUST preserve the existing number and MUST keep the Number field non-editable, in both draft and posted states.
- **FR-007**: Numbering MUST be scoped per business — one business's sequence MUST NOT affect another's.

### Key Entities

- **Invoice**: A business's sales or purchase invoice with a number, dates, lines, and a draft/posted lifecycle. The number uniquely identifies the invoice within its business.
- **Business (Tenant)**: Owns invoices and their number sequence(s); each business has independent numbering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users create an invoice without typing a number in under 2 minutes with a 100% success rate (zero "number required" errors).
- **SC-002**: The create dialog always shows the correct next number with no user edits possible.
- **SC-003**: Zero duplicate invoice numbers occur within a business for the same invoice type after this feature.
- **SC-004**: 100% of invoice edits preserve the original number unchanged, in draft and posted states.

## Assumptions

- Numbering format is `INV-` followed by a zero-padded 4-digit sequence (`INV-0001`, `INV-0002`, …), mirroring the customer `CUS-0001` / vendor `VEN-0001` pattern; sales and purchase invoices have independent per-type sequences within each business (clarified 2026-09-16).
- Numbering is monotonic and never reused, even if a draft invoice is deleted.
- Only invoice creation changes; customer, vendor, account, payment, and adjustment numbering behavior is out of scope.
- Existing invoice numbers are never migrated or altered; the new sequence applies to newly created invoices.
- Tenant isolation ensures each business's number sequence is independent and never crosses into another business's numbers.
- Payment numbers (`PAY-...`), adjustment numbers, and journal references are out of scope except for embedding the minted invoice number as they do today.
