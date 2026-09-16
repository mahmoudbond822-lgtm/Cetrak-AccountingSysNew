# Feature Specification: Auto Vendor Code

**Feature Branch**: `015-auto-vendor-code`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Apply what we did with customer code to vendor code"

## Clarifications

### Session 2026-09-16

- Q: What format should auto-assigned vendor codes use? → A: VEN-0001 (mirror of customer CUS-0001 pattern; legacy codes untouched).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a vendor with an auto-generated code (Priority: P1)

An accountant opens Purchases → Vendors → Create Vendor. The dialog shows a Code field that is visible but not editable (disabled/read-only) with a preview value starting at `VEN-0001`. The user fills in name and contact details, saves, and the new vendor appears in the list with that code. Opening Create again shows the next code (`VEN-0002`), incrementing by 1 for every saved vendor.

**Why this priority**: This mirrors the reported customer-code pain — creation currently fails with "Vendor code is required" when no code is typed. Showing an auto, non-editable code removes the blocker and is the whole value of the request.

**Independent Test**: Can be fully tested by opening the create dialog (code visible, not editable), saving with only a name, and confirming the saved vendor carries the shown code.

**Acceptance Scenarios**:

1. **Given** an empty vendor list, **When** the user opens Create Vendor, **Then** the Code field is visible, disabled, and shows `VEN-0001`.
2. **Given** the create dialog with the shown code, **When** the user saves a valid vendor, **Then** creation succeeds with no "code required" error and the saved vendor has exactly the shown code.
3. **Given** one saved vendor (`VEN-0001`), **When** the user opens Create Vendor again, **Then** the Code field shows `VEN-0002`.

### User Story 2 - Codes increment by 1 per saved vendor (Priority: P2)

Each time a vendor is saved, the system automatically increments the code by 1 from the highest existing code for that business. This ensures sequential, gap-free numbering within each business.

**Why this priority**: Guarantees that every new vendor gets a unique, incrementing code without manual entry, eliminating the "code required" error entirely.

**Independent Test**: Can be fully tested by creating several vendors in a row and confirming every code increments by exactly 1 from the previous.

**Acceptance Scenarios**:

1. **Given** one saved vendor (`VEN-0001`), **When** the user saves a second vendor, **Then** the second vendor gets `VEN-0002`.
2. **Given** five saved vendors (VEN-0001 through VEN-0005), **When** a sixth vendor is saved, **Then** the sixth vendor gets `VEN-0006`.
3. **Given** gaps from previously deleted vendors, **When** a new vendor is saved, **Then** the code assigns the next free sequential value (gaps are not reused).

### User Story 3 - Code is preserved and read-only on edit (Priority: P3)

Once a vendor exists, its code is shown but can never be edited or blanked through the edit dialog. This prevents accidental drift that would break historical references (e.g., purchase invoices linked to the vendor).

**Why this priority**: Protects already-saved data integrity. Lower priority than creation because it only guards existing records, but still essential for data consistency.

**Independent Test**: Can be fully tested by editing an existing vendor's name and confirming the code is unchanged.

**Acceptance Scenarios**:

1. **Given** an existing vendor, **When** a user edits name or contact details and saves, **Then** the code is unchanged.
2. **Given** the edit dialog, **When** viewed, **Then** the Code field is visible but not editable.

---

### Edge Cases

- First vendor in a new business shows `VEN-0001`.
- Codes with gaps from deleted vendors are not reused; numbering keeps moving forward.
- Blank, whitespace, or missing code values submitted at creation are treated the same: the system assigns the next code.
- Two businesses creating their first vendors at the same time each get their own independent sequence starting at `VEN-0001`.
- Rapid successive saves in one business never produce the same code twice.
- Opening the dialog never consumes a code: cancelled or abandoned creates leave the sequence untouched, and a stale preview is resolved at save time with the next free code plus a note.
- Explicitly supplied codes keep current behavior: creating with an already-used code returns the existing vendor (idempotent, same as customer flow); an unused explicit code is honored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a vendor without the user typing a code.
- **FR-002**: The create-vendor dialog MUST display a Code field that is visible but not editable (disabled/read-only).
- **FR-003**: The displayed code MUST start at `VEN-0001` for the first vendor and increment by 1 (`VEN-0002`, `VEN-0003`, …) for each subsequently saved vendor.
- **FR-004**: System MUST assign the code authoritatively at save time and MUST NOT reject the save with a "code required" error. The dialog preview is a non-binding hint: if the previewed value was taken before save, the save MUST still succeed with the next free code and show the user the assigned code.
- **FR-005**: Every assigned code MUST be unique within the business; the system MUST skip values that would collide.
- **FR-006**: On edit, the system MUST preserve the existing code and MUST keep the Code field non-editable.
- **FR-007**: Numbering MUST be scoped per business — one business's sequence MUST NOT affect another's.

### Key Entities

- **Vendor**: A business's purchase vendor with a code, name, and contact details. The code uniquely identifies the vendor within its business.
- **Business (Tenant)**: Owns vendors and their code sequence; each business has an independent numbering sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users create a vendor without typing a code in under 1 minute with a 100% success rate (zero "code required" errors).
- **SC-002**: The create dialog always shows the correct next code (first `VEN-0001`, then +1 per saved vendor) with no user edits possible.
- **SC-003**: Zero duplicate vendor codes occur within a business after this feature.
- **SC-004**: 100% of vendor edits preserve the original code unchanged.

## Assumptions

- Numbering format is `VEN-` followed by a zero-padded 4-digit sequence (`VEN-0001`, `VEN-0002`, …), mirroring the customer `CUS-0001` format established in Feature 014 (confirmed in clarification session 2026-09-16; legacy `V-001`-style codes are never migrated or altered).
- Numbering is monotonic and never reused, even if a vendor is deleted.
- Explicit-code behavior is unchanged from today (idempotent create on duplicate code returns the existing vendor with 200; unused explicit codes are honored) — only blank/missing codes gain auto-assignment.
- Only vendor creation changes; customer, account, and invoice numbering behavior is out of scope.
- Existing vendor codes (including legacy formats such as `V-001`) are never migrated or altered; the new sequence applies to newly created vendors.
- Tenant isolation ensures each business's code sequence is independent and never crosses into another business's codes.
