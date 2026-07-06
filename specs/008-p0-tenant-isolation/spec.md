# Feature Specification: P0 Tenant Isolation

**Feature Branch**: `008-p0-tenant-isolation`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "P0 tenant isolation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Block Cross-Tenant Accounting References (Priority: P1)

As an accounting user working inside one company workspace, I need the system to reject any account or journal entry input that references another company's accounting records so that financial data cannot be leaked, linked, or modified across tenants.

**Why this priority**: This closes the highest-risk production blocker. Cross-tenant accounting references can corrupt financial records and expose confidential data between customers.

**Independent Test**: Create two company workspaces with separate accounting users and accounts. While authenticated in one workspace, attempt to create accounting records using account identifiers from the other workspace. The action must be rejected and no cross-workspace relationship may be created.

**Acceptance Scenarios**:

1. **Given** Tenant A and Tenant B each have their own accounts, **When** a Tenant A user creates a child account using a Tenant B account as the parent, **Then** the system rejects the request and no child account is created.
2. **Given** Tenant A and Tenant B each have their own accounts, **When** a Tenant A user creates a journal entry line using a Tenant B account, **Then** the system rejects the request and no journal entry is created.
3. **Given** a Tenant A user submits a journal entry with one valid Tenant A account and one Tenant B account, **When** the entry is validated, **Then** the entire entry is rejected and no partial accounting record is saved.

---

### User Story 2 - Preserve Authorized Same-Tenant Accounting Work (Priority: P1)

As an authorized accounting user, I need valid same-tenant account hierarchy and journal entry workflows to continue working so that the isolation fix does not interrupt normal accounting operations.

**Why this priority**: The security fix must not break core accounting workflows for legitimate users in their own workspace.

**Independent Test**: In a single workspace, create parent and child accounts, create a balanced journal entry using accounts from that same workspace, and confirm the records are accepted and visible only within that workspace.

**Acceptance Scenarios**:

1. **Given** a Tenant A user has accounting access, **When** they create a child account under a Tenant A parent account, **Then** the account is created successfully.
2. **Given** a Tenant A user has accounting access and valid Tenant A accounts, **When** they create a balanced journal entry using only Tenant A accounts, **Then** the entry is created successfully.
3. **Given** a Tenant B user views accounting records after Tenant A creates records, **When** they list or retrieve accounting data, **Then** Tenant A records are not visible to Tenant B.

---

### User Story 3 - Provide Safe Rejection Feedback (Priority: P2)

As an accounting user, I need invalid cross-tenant references to fail with a clear but non-revealing error so that I can correct my input without learning whether another tenant's records exist.

**Why this priority**: Helpful errors reduce user confusion, while non-revealing errors prevent account enumeration and data leakage.

**Independent Test**: Submit accounting records with unknown, inaccessible, and cross-tenant account identifiers. Confirm each failure is reported consistently without exposing another tenant's account name, type, balance, or existence.

**Acceptance Scenarios**:

1. **Given** a Tenant A user submits a reference to an inaccessible account, **When** the request fails, **Then** the error does not disclose the other tenant's account details.
2. **Given** a Tenant A user submits an unknown account identifier, **When** the request fails, **Then** the error is handled consistently with inaccessible accounts.
3. **Given** a Tenant A user corrects the input to use only Tenant A accounts, **When** the request is resubmitted, **Then** the valid accounting workflow succeeds.

---

### Edge Cases

- What happens when an account identifier exists but belongs to another tenant? The system must reject it as inaccessible and must not disclose the other tenant's account details.
- What happens when a journal entry mixes accessible and inaccessible accounts? The whole entry must be rejected; no header, line, or partial financial record may be saved.
- What happens when a parent account identifier is inaccessible? The child account must not be created.
- What happens when an account identifier is malformed or unknown? The request must fail safely with a user-correctable error.
- What happens when the authenticated user belongs to multiple tenants? Only records belonging to the active tenant context may be accepted for the current action.
- What happens when a tenant has no accounts? Attempts to create journal entries must fail safely until valid same-tenant accounts exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate every account reference in accounting write operations against the user's active tenant before accepting the operation.
- **FR-002**: System MUST reject child account creation when the requested parent account does not belong to the user's active tenant.
- **FR-003**: System MUST reject journal entry creation when any journal line references an account outside the user's active tenant.
- **FR-004**: System MUST reject the entire accounting operation when any included account reference is inaccessible; partial records MUST NOT be saved.
- **FR-005**: System MUST preserve successful account hierarchy creation when all referenced accounts belong to the user's active tenant.
- **FR-006**: System MUST preserve successful balanced journal entry creation when all referenced accounts belong to the user's active tenant.
- **FR-007**: System MUST return safe validation feedback for inaccessible account references without exposing another tenant's account name, account type, balance, transaction history, or existence.
- **FR-008**: System MUST keep accounting list, detail, ledger, and report views limited to records from the user's active tenant.
- **FR-009**: System MUST include regression coverage for cross-tenant parent account references, cross-tenant journal line references, and mixed-tenant journal entries.
- **FR-010**: System MUST verify that authorized users who belong to more than one tenant can only reference records from the currently active tenant for the current accounting action.
- **FR-011**: System MUST ensure rejected cross-tenant attempts do not alter financial balances, reports, ledgers, account hierarchies, or journal entry counts for either tenant.
- **FR-012**: System MUST treat tenant isolation failures as production-blocking defects until all acceptance scenarios pass.

### Key Entities *(include if feature involves data)*

- **Tenant**: A customer workspace or company boundary. Accounting data from one tenant must never be accepted into another tenant's accounting records.
- **Accounting User**: An authenticated user with accounting permissions within one or more tenants. Their current tenant context determines which records they may reference.
- **Account**: A tenant-owned financial account that may optionally have a parent account from the same tenant.
- **Journal Entry**: A tenant-owned accounting transaction composed of multiple journal lines. Every referenced account must belong to the same active tenant as the journal entry.
- **Journal Entry Line**: A debit or credit line linked to one account. Lines must not link a tenant's journal entry to another tenant's account.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tested cross-tenant account parent reference attempts are rejected before any account is created.
- **SC-002**: 100% of tested cross-tenant journal entry account reference attempts are rejected before any journal entry or line is saved.
- **SC-003**: 100% of tested mixed-tenant journal entries leave both tenants' account balances, ledgers, reports, and journal entry counts unchanged.
- **SC-004**: 100% of existing same-tenant account creation and balanced journal entry workflows continue to complete successfully after the isolation fix.
- **SC-005**: Error messages for inaccessible account references disclose 0 tenant-specific account details from another tenant.
- **SC-006**: Isolation validation completes quickly enough that accounting users receive success or failure feedback during normal form submission without noticeable delay.

## Assumptions

- The feature applies to the existing accounting module and focuses on account hierarchy and journal entry write paths first because those are the confirmed P0 risks.
- Existing authentication, tenant selection, and role-based accounting access remain in place and are not redesigned by this feature.
- Unknown and inaccessible account references may share the same user-facing error behavior to avoid leaking record existence.
- The active tenant context is the source of truth for determining which accounting records are valid for the current action.
- Backup/DR, AI cost controls, billing, and deployment readiness are separate production-readiness workstreams and are outside this feature's scope.
