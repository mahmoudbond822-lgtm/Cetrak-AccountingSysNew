# Feature Specification: Team Invitations

**Feature Branch**: `002-team-invitations`

**Created**: 2026-06-14

**Status**: Draft

**Input**: User description: "Admin invites team members to the organization"

## Clarifications

### Session 2026-06-14

- Q: How does an existing user discover they've been invited to a new tenant — in-app notification system or passive discovery? → A: Passive — no notification system. The new tenant simply appears in the tenant list on next login. No in-app notification infrastructure is built in this feature.

### Session 2026-06-14 (Polish)

- Q: Should inviting an existing member of a tenant be rejected or allowed? → A: Allowed — an admin can invite any email, even if the person is already a member. The invitation acts as a pending invite they can accept or that can be cancelled.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin invites a new member via email (Priority: P1)

A company admin wants to add an accountant to their ERP system. They go to team management, enter the person's email and select a role, and send an invitation. The invited person receives an invitation link, registers an account, and automatically gains access to the company's data with the assigned role.

**Why this priority**: Team collaboration is core to the ERP value proposition. Without inviting others, a business owner cannot delegate accounting or management tasks.

**Independent Test**: An admin can create an invitation for a new email, and that person can register with the invitation token, see the company in their tenant list, and access it with the correct role.

**Acceptance Scenarios**:

1. **Given** an authenticated admin on the team management page, **When** they enter a new email, select a role (accountant or manager), and confirm, **Then** the system creates a pending invitation and returns its details.
2. **Given** a pending invitation exists for an email, **When** a person registers using that email and the invitation token, **Then** they are authenticated, auto-linked to the inviting tenant with the specified role, and redirected to the dashboard.
3. **Given** a pending invitation that is 7+ days old, **When** a person attempts to register with its token, **Then** registration is rejected with an expired invitation error.

---

### User Story 2 - Existing user invited to a new tenant (Priority: P1)

A person who already has a system account (belonging to a different company) is invited to another tenant. They should not re-register — the new tenant simply appears in their tenant list after their next login.

**Why this priority**: Real businesses have accountants who work across multiple clients. These users must be able to access multiple tenants without managing separate accounts.

**Independent Test**: An existing user who is invited to a new tenant sees that tenant appear in their tenant selection screen on next login without any additional signup.

**Acceptance Scenarios**:

1. **Given** an existing registered user, **When** an admin sends them an invitation to a new tenant, **Then** the new tenant appears in the user's tenant list with the assigned role on their next login.
2. **Given** an existing user invited to a new tenant, **When** they log in, **Then** they see both their original tenant and the new tenant in the tenant selection screen.

---

### User Story 3 - Admin manages team members and roles (Priority: P2)

An admin can view all current members of their tenant, change their roles, or remove them from the tenant. The last admin of a tenant cannot be removed or have their role changed to protect against orphaned tenants.

**Why this priority**: Team composition changes over time. Admins need to manage access and ensure at least one admin always remains.

**Independent Test**: An admin can navigate to team management, see all members with their roles, change a member's role, and remove a non-admin member.

**Acceptance Scenarios**:

1. **Given** an admin viewing the team management page, **When** they look at the member list, **Then** they see each member's name, email, role, and join date.
2. **Given** an admin on the team management page, **When** they change a member's role from accountant to manager, **Then** the change takes effect immediately.
3. **Given** an admin on the team management page, **When** they try to remove a member who is not the last admin, **Then** the member is removed successfully.
4. **Given** a tenant with only one admin, **When** that admin tries to change their own role to a non-admin role or remove themselves, **Then** the action is blocked with an error explaining that at least one admin must remain.

---

### User Story 4 - Admin cancels a pending invitation (Priority: P3)

An admin can view all pending invitations and cancel any that were sent in error or are no longer needed.

**Why this priority**: Prevents accumulation of stale invitations and reduces confusion.

**Independent Test**: An admin can see a list of pending invitations and cancel any of them.

**Acceptance Scenarios**:

1. **Given** an admin on the team management page, **When** they view pending invitations, **Then** they see each invitation's email, role, expiry date, and status.
2. **Given** an admin viewing pending invitations, **When** they cancel an invitation, **Then** it is no longer valid and cannot be used for registration.

---

### Edge Cases

- What happens when an admin tries to invite someone who is already a member of the tenant? → The invitation is allowed — the admin can create a pending invitation for any email, even an existing member's. The member can use the token to accept or the admin can cancel it later.
- What happens when an admin tries to invite someone who already has a pending invitation for the same tenant? → The invitation is rejected with an error that a pending invitation already exists for that email. The admin can cancel the existing invitation and create a new one.
- What happens when an invitation token is used twice? → The first successful use marks it as accepted; subsequent attempts are rejected.
- How does the system handle a tenant with only one admin trying to change their role? → Blocked with error explaining that at least one admin must remain.
- What happens when a non-admin user tries to access team management endpoints? → All team management endpoints require the admin role; non-admin requests are rejected with 403 Forbidden.
- How does the system handle an invalid or malformed invitation token? → Returns a 400 error with an appropriate message.
- What happens to invitations when a tenant is suspended or cancelled? → Deferred — tenant lifecycle management (suspension, cancellation) is not within this feature's scope. Pending invitations remain valid until they expire or are accepted. When tenant lifecycle management is implemented, invitation validation should be updated accordingly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An admin user MUST be able to invite a new user to their tenant by providing an email address and selecting a role.
- **FR-002**: The invitation MUST generate a unique, secure token that expires after 7 days.
- **FR-003**: An invited person MUST be able to register using their email and the invitation token, automatically joining the inviting tenant with the specified role.
- **FR-004**: An existing user invited to a new tenant MUST NOT need to re-register — the new membership MUST appear in their tenant list on next login.
- **FR-005**: An admin MUST be able to cancel a pending invitation, which invalidates its token.
- **FR-006**: An admin MUST be able to view all current members of their tenant with their names, emails, roles, and join dates.
- **FR-007**: An admin MUST be able to change a member's role within the tenant.
- **FR-008**: An admin MUST be able to remove a member from the tenant, provided the member is not the last admin.
- **FR-009**: The system MUST protect against removing or demoting the last admin of a tenant.
- **FR-010**: Only admin role users MAY access team management endpoints.

### Key Entities *(include if feature involves data)*

- **Invitation**: Represents a pending invitation from an admin to a new team member. Tracks the target email, assigned role, unique token, expiry date, and acceptance status (accepted_at timestamp or null). Associated with a specific tenant.
- **Membership**: (Existing entity) Links a User to a Tenant with a specific role. This feature expands Membership to support role changes, member removal, and last-admin protection.
- **User**: (Existing entity) An individual who can access the system. This feature requires User lookup by email for existing-user invitation flow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can invite a new member in under 30 seconds from opening the team management page.
- **SC-002**: An invited new user can complete registration and access the tenant in under 2 minutes.
- **SC-003**: An existing user invited to a new tenant sees the tenant in their list within 5 seconds of their next login.
- **SC-004**: All team management operations (list members, change role, remove member, cancel invitation) respond within 2 seconds.
- **SC-005**: A non-admin user cannot access any team management endpoint under any circumstance.
- **SC-006**: An invitation token that is expired, already accepted, or cancelled is rejected with a clear error message.

## Assumptions

- This feature builds on top of the existing authentication system (JWT, User model, Membership model) established in the project foundation.
- Email delivery of invitation links is handled by a third-party email service (SendGrid, AWS SES, etc.) — actual email sending is out of scope for this feature; the system generates the invitation token and the frontend displays/copies the invitation URL.
- The invitation URL format is: `{frontend_url}/register?token={invitation_token}`.
- Team management is a web-based UI within the existing application — no mobile-specific UI is required.
- Roles are limited to the three existing roles: Admin, Accountant, Manager.
- Tenant plan limits (e.g., max users per plan) are not enforced during this phase but the data model should accommodate future limits.
