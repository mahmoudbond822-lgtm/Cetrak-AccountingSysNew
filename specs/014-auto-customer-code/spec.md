# Feature Specification: Auto Customer Code

**Feature Branch**: `014-auto-customer-code`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "{\"code\":[\"This field is required.\"]} add a customer code in create customer dialog as a field not enabled with CUS-0001 and add 1 every saving customer"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a customer with an auto-generated code (Priority: P1)

An accountant opens Sales → Customers → Create Customer. The dialog shows a Code field that is visible but not editable (disabled/read-only) with a preview value starting at `CUS-0001`. The user fills in name and contact details, saves, and the new customer appears in the list with that code. Opening Create again shows the next code (`CUS-0002`), incrementing by 1 for every saved customer.

**Why this priority**: This is the reported pain — creation currently fails with "This field is required" on code. Showing an auto, non-editable code removes the blocker and is the whole value of the request.

**Independent Test**: Can be fully tested by opening the create dialog (code visible, not editable), saving with only a name, and confirming the saved customer carries the shown code.

**Acceptance Scenarios**:

1. **Given** an empty customer list, **When** the user opens Create Customer, **Then** the Code field is visible, disabled, and shows `CUS-0001`.
2. **Given** the create dialog with the shown code, **When** the user saves a valid customer, **Then** creation succeeds with no "code required" error and the saved customer has exactly the shown code.
3. **Given** one saved customer (`CUS-0001`), **When** the user opens Create Customer again, **Then** the Code field shows `CUS-0002`.

### User Story 2 - Codes increment by 1 per saved customer (Priority: P2)

Each time a customer is saved, the system automatically increments the code by 1 from the highest existing code for that business. This ensures sequential, gap-free numbering within each business.

**Why this priority**: Guarantees that every new customer gets a unique, incrementing code without manual entry, eliminating the "code required" error entirely.

**Independent Test**: Can be fully tested by creating several customers in a row and confirming every code increments by exactly 1 from the previous.

**Acceptance Scenarios**:

1. **Given** one saved customer (`CUS-0001`), **When** the user saves a second customer, **Then** the second customer gets `CUS-0002`.
2. **Given** five saved customers (CUS-0001 through CUS-0005), **When** a sixth customer is saved, **Then** the sixth customer gets `CUS-0006`.
3. **Given** gaps from previously deleted customers, **When** a new customer is saved, **Then** the code assigns the next free sequential value (gaps are not reused).

### User Story 3 - Code is preserved and read-only on edit (Priority: P3)

Once a customer exists, its code is shown but can never be edited or blanked through the edit dialog. This prevents accidental drift that would break historical references.

**Why this priority**: Protects already-saved data integrity. Lower priority than creation because it only guards existing records, but still essential for data consistency.

**Independent Test**: Can be fully tested by editing an existing customer's name and confirming the code is unchanged.

**Acceptance Scenarios**:

1. **Given** an existing customer, **When** a user edits name or contact details and saves, **Then** the code is unchanged.
2. **Given** the edit dialog, **When** viewed, **Then** the Code field is visible but not editable.

---

### Edge Cases

- First customer in a new business shows `CUS-0001`.
- Codes with gaps from deleted customers are not reused; numbering keeps moving forward.
- Blank, whitespace, or missing code values submitted at creation are treated the same: the system assigns the next code.
- Two businesses creating their first customers at the same time each get their own independent sequence starting at `CUS-0001`.
- Rapid successive saves in one business never produce the same code twice.
- Opening the dialog never consumes a code: cancelled or abandoned creates leave the sequence untouched, and a stale preview is resolved at save time with the next free code plus a note.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a customer without the user typing a code.
- **FR-002**: The create-customer dialog MUST display a Code field that is visible but not editable (disabled/read-only).
- **FR-003**: The displayed code MUST start at `CUS-0001` for the first customer and increment by 1 (`CUS-0002`, `CUS-0003`, …) for each subsequently saved customer.
- **FR-004**: System MUST assign the code authoritatively at save time and MUST NOT reject the save with a "code required" error. The dialog preview is a non-binding hint: if the previewed value was taken before save, the save MUST still succeed with the next free code and show the user the assigned code.
- **FR-005**: Every assigned code MUST be unique within the business; the system MUST skip values that would collide.
- **FR-006**: On edit, the system MUST preserve the existing code and MUST keep the Code field non-editable.
- **FR-007**: Numbering MUST be scoped per business — one business's sequence MUST NOT affect another's.

### Key Entities

- **Customer**: A business's sales customer with a code, name, and contact details. The code uniquely identifies the customer within its business.
- **Business (Tenant)**: Owns customers and their code sequence; each business has an independent numbering sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users create a customer without typing a code in under 1 minute with a 100% success rate (zero "code required" errors).
- **SC-002**: The create dialog always shows the correct next code (first `CUS-0001`, then +1 per saved customer) with no user edits possible.
- **SC-003**: Zero duplicate customer codes occur within a business after this feature.
- **SC-004**: 100% of customer edits preserve the original code unchanged.

## Assumptions

- Numbering format is `CUS-` followed by a zero-padded 4-digit sequence (`CUS-0001`, `CUS-0002`, …).
- Numbering is monotonic and never reused, even if a customer is deleted.
- Only customer creation changes; vendor, account, and invoice numbering behavior is out of scope.
- Existing customer codes are never migrated or altered.
- Tenant isolation ensures each business's code sequence is independent and never crosses into another business's codes.