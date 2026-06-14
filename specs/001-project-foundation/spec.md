# Feature Specification: Project Foundation

**Feature Branch**: `001-project-foundation`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "F1 — Foundation: Django project setup, Docker, PostgreSQL, multi-tenancy, custom User model, JWT auth, Login/Register APIs, Login & Register frontend pages"

## Clarifications

### Session 2026-06-13

- Q: Invitation flow — what if the invited person already has a system account? → A: They receive a notification that they've been added to a new organization, and it appears in their tenant switcher on next login.
- Q: What lifecycle states should a user account support? → A: Three states: Active (registered and active), Invited/Pending (invited but not yet registered), Disabled (admin has removed access — cannot log in).
- Q: Should tenants have lifecycle states? What happens on deactivation? → A: Yes — Active, Suspended, Cancelled. On suspension or cancellation, all active sessions are terminated immediately and users cannot log in. Data is preserved for suspended tenants; cancelled tenants are soft-deleted.
- Q: Multi-tenant login — when does the user pick the tenant? → A: User logs in first (single login form, no tenant field). If they belong to only one tenant, they go straight to the dashboard. If they belong to multiple, they pick from a tenant list after authentication.
- Q: How long should user sessions persist before requiring re-authentication? → A: 24-hour session by default. Optional "remember me" checkbox extends to 30 days. Session expires immediately on logout.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Business owner signs up and logs in (Priority: P1)

A small business owner wants to start using the ERP system. They visit the website, create their company account, set up their admin user, and log in to access the dashboard for the first time.

**Why this priority**: Without the ability to create an account and log in, no user can access any part of the system. This is the foundational gate that every other feature depends on.

**Independent Test**: A new user can visit the signup page, complete registration with a company name, email, and password, then immediately log in and see an empty dashboard with their company name displayed.

**Acceptance Scenarios**:

1. **Given** a new visitor on the registration page, **When** they enter their email, company name, and password and submit, **Then** their account is created, their company (tenant) is provisioned, and they are logged in automatically.
2. **Given** a registered user on the login page, **When** they enter their correct email and password and optionally check "remember me", **Then** they are authenticated. If they belong to one tenant, they are redirected to the main dashboard. If they belong to multiple tenants, they see a tenant selection screen first.
3. **Given** a registered user on the login page, **When** they enter an incorrect password, **Then** they see a clear error message and are not logged in.

---

### User Story 2 - Admin invites team members to the organization (Priority: P2)

An admin user wants to add an accountant to their company's ERP system. They invite the team member via email, who then creates their own login and gains access to the same company data with appropriate permissions.

**Why this priority**: Small businesses typically have at least 2-3 people (owner, accountant) who need access. This enables team collaboration within a shared company account.

**Independent Test**: An admin can navigate to team management, enter a new member's email address and assign a role, and that person can then register and access the same company's data with the assigned permissions.

**Acceptance Scenarios**:

1. **Given** an authenticated admin user on the team management page, **When** they enter a new email, select a role (accountant or manager), and confirm, **Then** the system registers the invitation and the new user can complete registration linked to the same company.
2. **Given** an invited user completing registration, **When** they use the same email, **Then** they are automatically associated with the inviting company and assigned the specified role.
3. **Given** an invited person who already has a system account (belonging to a different tenant), **When** the admin sends the invitation, **Then** the existing user receives a notification and the new tenant appears in their tenant switcher on next login — no separate signup needed.
4. **Given** an admin viewing the team list, **When** they look at all members, **Then** they see each user's name, email, role, and join date.

---

### User Story 3 - User manages their profile and resets password (Priority: P3)

A user wants to update their display name or change their password. They navigate to settings, make the change, and it takes effect immediately.

**Why this priority**: Users should have basic account self-service to reduce support burden and maintain security.

**Independent Test**: A logged-in user can navigate to profile settings, change their display name and password, log out, and log back in with the new password.

**Acceptance Scenarios**:

1. **Given** a logged-in user on the profile page, **When** they update their display name and save, **Then** the change is reflected immediately throughout the system.
2. **Given** a logged-in user on the profile page, **When** they change their password by entering the current password and a new password, **Then** they are required to log in again with the new password.
3. **Given** a user who forgot their password on the login page, **When** they click "Forgot Password" and enter their email, **Then** they receive a password reset link.

---

### Edge Cases

- What happens when a disabled user tries to log in? → A: Login is rejected with a message that the account has been disabled and to contact their admin.
- What happens when someone tries to register with an already-used email? → A: Registration is rejected with a 400 error indicating the email is already in use.
- How does the system handle a user belonging to multiple organizations? → A: Users see a tenant switcher in the UI. They can switch between organizations they belong to without re-authenticating. Each switch re-scopes data access to the selected tenant.
- What happens when the last admin of an organization tries to change their role? → A: The action is blocked. At least one admin must remain. The user must assign another admin first before changing their role.
- How does the system respond when a tenant's user count exceeds their plan limit?
- What happens to user sessions when a tenant is deactivated? → A: On suspension or cancellation, all active sessions for all users of that tenant are terminated immediately. Users see a message that their organization's access has been suspended.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: New users MUST be able to register a new account with their email and create a new company (tenant) simultaneously.
- **FR-002**: Registered users MUST be able to log in using their email and password.
- **FR-003**: Users MUST be able to log out, which terminates their current session.
- **FR-004**: An admin user MUST be able to invite new users to their tenant by email and assign them a role.
- **FR-005**: Invited users MUST be able to complete registration and automatically join the inviting tenant.
- **FR-006**: Users MUST be able to view and update their own profile (display name, email).
- **FR-007**: Users MUST be able to change their password, requiring the current password for verification.
- **FR-008**: Users who forget their password MUST be able to request a password reset via email.
- **FR-009**: Each user MUST belong to at least one tenant, and the system MUST enforce data isolation so users only see data belonging to their own tenant.
- **FR-010**: Three roles MUST exist: Admin (full access), Accountant (accounting + sales + purchases), Manager (reports and dashboard read-only).
- **FR-011**: A user MUST NOT be able to access any system page or API without being authenticated.
- **FR-012**: Registration MUST NOT require email verification for the MVP phase.
- **FR-013**: User accounts MUST support three lifecycle states: Active (can log in and use the system), Invited/Pending (invited but not yet registered), and Disabled (access revoked by admin — cannot log in).
- **FR-014**: Tenants MUST support three lifecycle states: Active, Suspended (data preserved, access blocked), and Cancelled (soft-deleted). Suspending or cancelling a tenant MUST terminate all active sessions for that tenant immediately.
- **FR-015**: User sessions MUST expire after 24 hours by default. A "remember me" option MUST extend the session to 30 days. Sessions MUST terminate immediately on explicit logout.

### Key Entities *(include if feature involves data)*

- **Tenant**: Represents a company or organization using the ERP system. Each tenant has its own isolated data scope. Tenants have a lifecycle state: Active, Suspended, or Cancelled.
- **User**: An individual person who can access the system. Users authenticate with email and password. Each user has a lifecycle state: Active, Invited/Pending, or Disabled.
- **Membership**: Links a User to a Tenant with a specific Role. A user can belong to multiple tenants with different roles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new business owner can complete registration and access the system in under 3 minutes without assistance.
- **SC-002**: A returning user can log in within 5 seconds of submitting their credentials.
- **SC-003**: Users from different tenants cannot see each other's data under any circumstances.
- **SC-004**: An admin can invite a new team member and have them access the shared tenant in under 5 minutes.
- **SC-005**: Password reset requests are fulfilled within 1 minute of the user clicking the reset link.
- **SC-006**: 99% of login attempts succeed on the first try with correct credentials (excluding network errors).

## Assumptions

- Users have reliable internet connectivity and a modern web browser.
- Email service for password reset and invitations will use a third-party email provider (SendGrid, AWS SES, etc.).
- Email verification is not required for MVP — a user's email is considered verified upon registration.
- Mobile app support is out of scope for the MVP phase.
- The system will start with three fixed roles: Admin, Accountant, and Manager. Custom roles are not supported at this stage.
- Users who forget their password can receive reset emails — no SMS or other recovery methods are needed.
- Tenant plan limits (e.g., max users per plan) are not enforced during MVP but the data model should accommodate them.
- The ERP serves small businesses with up to 50 users per tenant in the MVP phase.
