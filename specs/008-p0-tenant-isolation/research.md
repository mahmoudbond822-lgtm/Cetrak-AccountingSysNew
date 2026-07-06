# Research: P0 Tenant Isolation

## Decision: Scope tenant validation to active tenant for all accounting account references

**Rationale**: The confirmed P0 gap is that account references in account hierarchy and journal entry creation can resolve records outside the active tenant. The smallest production-safe fix is to validate those references against the active tenant before accepting the operation.

**Alternatives considered**: A broader multi-tenant manager redesign was considered but rejected for this feature because it would increase blast radius. This feature should close the confirmed P0 blocker first and leave broader enforcement patterns for a separate hardening pass.

## Decision: Treat unknown and inaccessible account references consistently

**Rationale**: Returning different user-facing errors for missing records versus other-tenant records can disclose whether another tenant's account exists. Safe validation should reject both without exposing account name, type, balance, transaction history, or tenant identity.

**Alternatives considered**: Detailed errors were considered for usability, but rejected because security and privacy matter more for a multi-tenant accounting boundary.

## Decision: Reject mixed-tenant journal entries as an all-or-nothing operation

**Rationale**: A journal entry with any inaccessible account reference is unsafe. Saving only valid lines or creating an entry header without all valid lines would corrupt accounting state and violate the feature spec.

**Alternatives considered**: Partial acceptance was rejected because accounting records must be complete and balanced. User correction before save is safer and easier to audit.

## Decision: Add regression tests to the existing accounting API suite

**Rationale**: Existing accounting tests already create tenants, users, accounts, and journal entries. Adding tests there directly proves the vulnerable user-facing behavior and protects against future regressions.

**Alternatives considered**: Isolated unit tests were considered but are insufficient on their own because the bug appears at the API validation boundary with authentication and active tenant context.

## Decision: Avoid schema and dependency changes for this P0 fix

**Rationale**: The confirmed issue is reference validation, not a missing table or persisted field. Keeping the fix dependency-free and migration-free reduces production risk and keeps the change focused.

**Alternatives considered**: Database-level tenant constraints were considered for future hardening, but they require schema design beyond the immediate P0 closure and are better handled as a follow-up after the API-level blocker is fixed.
