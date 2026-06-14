# Quickstart Validation: Team Invitations

## Prerequisites

- Foundation project is set up and running (backend + database)
- JWT auth is working (User Story 1 complete)
- At least one admin user and tenant exist

## Setup

```bash
# Run migrations for new Invitation model
docker-compose exec backend python manage.py makemigrations accounts
docker-compose exec backend python manage.py migrate

# Run tests
docker-compose exec backend pytest apps/accounts/tests/ -v
```

## Validation Scenarios

### Scenario 1: Admin creates an invitation

```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "AdminPass123!"}' | jq -r '.access')

TENANT_ID=$(curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq -r '.active_tenant.id')

# Create invitation
curl -X POST http://localhost:8000/api/v1/tenants/invitations \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"email": "newaccountant@example.com", "role": "accountant"}'
```

**Expected**: 201 Created. Returns invitation details with status "pending" and 7-day expiry.

---

### Scenario 2: New user registers with invitation token

```bash
# Extract invitation token from Step 1 (or from database)
INVITATION_TOKEN="<token_from_step_1>"

# Register with invitation
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"newaccountant@example.com\", \"password\": \"NewPass123!\", \"invitation_token\": \"$INVITATION_TOKEN\"}"
```

**Expected**: 201 Created. User is auto-linked to the inviting tenant with role "accountant". No new tenant is created.

---

### Scenario 3: Existing user is invited to a new tenant

```bash
# Login as the existing user
EXISTING_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "existing@example.com", "password": "ExistingPass123!"}' | jq -r '.access')

# Login response should show the new tenant in the tenants array
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $EXISTING_TOKEN"
```

**Expected**: The user's tenant list includes both their original tenant and the newly invited tenant.

---

### Scenario 4: Admin views team members

```bash
curl http://localhost:8000/api/v1/tenants/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"
```

**Expected**: 200 OK. Returns list of all members with user_id, email, display_name, role, status, joined_at.

---

### Scenario 5: Admin changes a member's role

```bash
# Change member role (use actual user_id from members list)
curl -X PATCH http://localhost:8000/api/v1/tenants/members/<user_id>/role \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"role": "manager"}'
```

**Expected**: 200 OK. Member's role updated immediately.

---

### Scenario 6: Last admin protection

```bash
# Try to change the last admin's role away from admin
curl -X PATCH http://localhost:8000/api/v1/tenants/members/<admin_user_id>/role \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"role": "accountant"}'
```

**Expected**: 400 Bad Request. Error message: "Cannot change the role of the last admin."

---

### Scenario 7: Admin cancels an invitation

```bash
# List invitations to get the invitation ID
INVITATION_ID=$(curl -s http://localhost:8000/api/v1/tenants/invitations \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" | jq -r '.results[0].id')

# Cancel the invitation
curl -X DELETE http://localhost:8000/api/v1/tenants/invitations/$INVITATION_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"
```

**Expected**: 204 No Content. Token is no longer valid for registration.

---

### Scenario 8: Non-admin cannot access team endpoints

```bash
# Login as a non-admin user (accountant/manager)
USER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "accountant@example.com", "password": "AccPass123!"}' | jq -r '.access')

# Try to access team endpoints
curl http://localhost:8000/api/v1/tenants/members \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"
```

**Expected**: 403 Forbidden.

---

## Running Tests

```bash
# Run all team tests
docker-compose exec backend pytest apps/accounts/tests/test_team_api.py -v

# Run all accounts tests
docker-compose exec backend pytest apps/accounts/tests/ -v

# Run with coverage
docker-compose exec backend pytest apps/accounts/tests/ --cov=apps.accounts --cov-report=term-missing
```

## Expected Test Coverage Areas

- **Invitations**: create (admin), create duplicate (pending email), create as non-admin, list pending, cancel, expired token registration, invalid token registration
- **Members**: list (admin), list (non-admin = 403), change role, change last admin role (blocked), remove member, remove last admin (blocked)
- **Registration**: with valid invitation token, with expired token, with cancelled token, with token matching different email
- **Tenant isolation**: invitations and members are scoped to the authenticated tenant
