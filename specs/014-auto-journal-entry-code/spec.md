# Feature Specification: Auto Journal Entry Code

**Feature Branch**: `014-auto-journal-entry-code`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "Apply what we do with customer code and vendor code and Invoice number to journal entry start with this reference JE-YYYY-0001"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a journal entry with an auto-generated code (Priority: P1)

An accountant opens the Journal Entry creation form. The form shows a Reference/Code field that is visible but not editable (disabled/read-only) with a preview value starting at `JE-2026-0001`. The user fills in the date, description, and lines, saves, and the new journal entry appears in the list with that number. Opening the create form again shows the next number (`JE-2026-0002`), incrementing by 1 for each subsequently saved journal entry.

**Why this priority**: This is the reported pain — users cannot create journal entries because the code field is empty and the system rejects the save with "code required" error. Showing an auto, non-editable code removes the blocker and enables journal entry creation without requiring the user to know the code format or generate it.

**Independent Test**: Can be fully tested by opening the create journal entry form, saving with required fields only (date, at least 2 lines with accounts), and confirming the saved journal entry carries the shown code `JE-2026-0001`.

**Acceptance Scenarios**:

1. **Given** an empty journal entry list, **When** the user opens Create Journal Entry, **Then** the Code field is visible, disabled, and shows `JE-2026-0001`.
2. **Given** the create journal entry form with the shown code, **When** the user fills in required fields and saves, **Then** creation succeeds with no "code required" error and the saved journal entry has exactly the shown code.
3. **Given** one saved journal entry (`JE-2026-0001`), **When** the user opens Create Journal Entry again, **Then** the Code field shows `JE-2026-0002`.

### User Story 2 - Codes increment by 1 per save (Priority: P2)

Each time a journal entry is saved, the system automatically increments the code by 1 from the highest existing code for that business. This ensures sequential, gap-free numbering within each business.

**Why this priority**: Guarantees that every new journal entry gets a unique, incrementing code without manual entry, eliminating user confusion and ensuring proper audit trails.

**Independent Test**: Can be fully tested by creating several journal entries in a row and confirming each code increments by exactly 1 from the previous (`JE-2026-0001`, `JE-2026-0002`, `JE-2026-0003`, etc.).

**Acceptance Scenarios**:

1. **Given** one saved journal entry, **When** a second journal entry is saved, **Then** the second entry gets the next sequential code.
2. **Given** five saved journal entries (`JE-2026-0001` through `JE-2026-0005`), **When** a sixth journal entry is saved, **Then** the sixth entry gets `JE-2026-0006`.
3. **Given** gaps from previously deleted draft journal entries, **When** a new journal entry is saved, **Then** the code assigns the next sequential value (gaps are not reused).

### User Story 3 - Code is preserved and read-only after creation (Priority: P3)

Once a journal entry exists, its code is shown but can never be edited — not while a draft, not after posting — to protect the immutable audit trail.

**Why this priority**: Protects posted financial records and their journal references. Lower priority than creation because it only guards existing records, but essential for accounting integrity.

**Independent Test**: Can be fully tested by editing an existing journal entry's description or amount lines and confirming the code is unchanged.

**Acceptance Scenarios**:

1. **Given** an existing journal entry (draft or posted), **When** a user edits its description or lines and saves, **Then** the code is unchanged.
2. **Given** the edit journal entry form, **When** viewed, **Then** the Code field is visible but not editable.

### User Story 4 - Preview resolves to next available code (Priority: P4)

When opening the create journal entry form multiple times without saving, each time shows the next sequential code, and cancelled creates do not consume or skip codes.

**Why this priority**: Ensures users always see the correct next code even if they open multiple forms or cancel some drafts.

**Independent Test**: Can be fully tested by opening the create form multiple times, cancelling, then saving, and verifying no codes are skipped or duplicated.

**Acceptance Scenarios**:

1. **Given** one saved journal entry (`JE-2026-0001`), **When** the user opens the create form, cancels, then opens again and saves, **Then** the saved entry gets `JE-2026-0002` (not `JE-2026-0003`).
2. **Given** two users opening the create form simultaneously, **When** both save, **Then** the first save gets the previewed code and the second gets the next sequential code.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a journal entry without the user typing a code.
- **FR-002**: The create-journal-entry form MUST display a Reference field that is visible but not editable (disabled/read-only) with a preview value starting at `JE-2026-0001` for the first journal entry and incrementing by 1 (`JE-2026-0002`, `JE-2026-0003`, …) for each subsequently saved journal entry.
- **FR-003**: The displayed code MUST follow the format `JE-YYYY-NNNN` where YYYY is the current year and NNNN is a zero-padded 4-digit sequence number.
- **FR-004**: System MUST assign the code authoritatively at save time and MUST NOT reject the save with a "code required" error. The dialog preview is a non-binding hint: if the previewed value was taken before save, the save MUST still succeed with the next free code.
- **FR-005**: Every assigned code MUST be unique within the business; the system MUST skip values that would collide.
- **FR-006**: On edit, the system MUST preserve the existing code and MUST keep the Reference field non-editable, in both draft and posted states.
- **FR-007**: Numbering MUST be scoped per business — one business's sequence MUST NOT affect another's.

### Key Entities *(include if feature involves data)*

- **Journal Entry**: A business's accounting journal entry with a reference code, date, description, and account lines. The code uniquely identifies the journal entry within its business.
- **Business (Tenant)**: Owns journal entries and their reference code sequence; each business has an independent numbering sequence starting at `JE-YYYY-0001` for each year.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users create a journal entry without typing a code in under 2 minutes with a 100% success rate (zero "code required" errors).
- **SC-002**: The create journal entry form always shows the correct next code with no user edits possible.
- **SC-003**: Zero duplicate journal entry codes occur within a business after this feature.
- **SC-004**: 100% of journal entry edits preserve the original code unchanged, in draft and posted states.
- **SC-005**: Code format validation rejects malformed codes with a clear error message.

## Edge Cases

- First journal entry in a new business for a given year shows `JE-YYYY-0001` where YYYY is the current year.
- Codes with gaps from deleted journal entries are not reused; numbering keeps moving forward.
- Blank, whitespace, or missing code values submitted at creation are treated the same: the system assigns the next code.
- Two businesses creating their first journal entries at the same time each get their own independent sequence starting at `JE-YYYY-0001`.
- Rapid successive saves in one business never produce the same code twice.
- Opening the create form never consumes a code: cancelled or abandoned creates leave the sequence untouched.
- Existing journal entries with manually-entered codes are never migrated or altered.

## Assumptions

- Numbering format is `JE-` followed by the 4-digit year, a hyphen, and a zero-padded 4-digit sequence (`JE-2026-0001`, `JE-2026-0002`, …)
- The year component resets to `0001` at the start of each new year
- Numbering is monotonic and never reused, even if a journal entry is deleted
- Only journal entry creation changes; customer, vendor, account, and invoice numbering behavior is out of scope for this feature
- Tenant isolation ensures each business's code sequence is independent and never crosses into another business's codes
- The feature mirrors the pattern established for customer code (CUS-YYYY-0001), vendor code (VEN-YYYY-0001), and invoice number (INV-YYYY-0001)