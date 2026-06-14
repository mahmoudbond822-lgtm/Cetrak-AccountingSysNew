# Quickstart Validation: Project Foundation

## Prerequisites

- Docker and Docker Compose installed
- Git repository cloned
- Ports 8000 (backend), 3000 (frontend), 5432 (PostgreSQL) available

## Setup

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend python manage.py migrate

# Create database indexes
docker-compose exec backend python manage.py migrate

# Run tests
docker-compose exec backend pytest
```

## Validation Scenarios

### Scenario 1: New user registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com", "password": "Test1234!", "company_name": "Test Corp"}'
```

**Expected**: 201 Created. Response includes access token, refresh token, user object, and tenant object.

---

### Scenario 2: Login with correct credentials

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com", "password": "Test1234!", "remember_me": false}'
```

**Expected**: 200 OK. Response includes tokens and user data with active_tenant populated.

---

### Scenario 3: Login with wrong password

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com", "password": "wrongpassword"}'
```

**Expected**: 401 Unauthorized. Response includes error detail.

---

### Scenario 4: Access protected endpoint without token

```bash
curl http://localhost:8000/api/v1/auth/me
```

**Expected**: 401 Unauthorized.

---

### Scenario 5: Access protected endpoint with valid token

```bash
# First login to get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com", "password": "Test1234!"}' | jq -r '.access')

curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: <tenant_id_from_login>"
```

**Expected**: 200 OK. Returns user profile.

---

### Scenario 6: Invite a new member

```bash
curl -X POST http://localhost:8000/api/v1/tenants/invitations \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{"email": "accountant@example.com", "role": "accountant"}'
```

**Expected**: 201 Created. Returns invitation details.

---

### Scenario 7: Invited user registers and auto-joins tenant

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "accountant@example.com", "password": "Test1234!", "invitation_token": "<token_from_invitation>"}'
```

**Expected**: 201 Created. User is automatically linked to the inviting tenant.

---

### Scenario 8: Multi-tenant user login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "accountant@example.com", "password": "Test1234!"}'
```

**Expected**: 200 OK. Response includes multiple tenants in the tenants array and active_tenant is null.

---

### Scenario 9: Switch active tenant

```bash
curl -X POST http://localhost:8000/api/v1/tenants/switch/<other_tenant_id> \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: 200 OK. Returns new access token with updated tenant claim.

---

### Scenario 10: Password reset flow

```bash
# Request reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com"}'

# Expected: 204 No Content

# Confirm reset (use token from email/console)
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"token": "<reset_token>", "password": "NewPass5678!"}'

# Expected: 200 OK
```

## Running Tests

```bash
# Run all tests
docker-compose exec backend pytest -v

# Run specific test file
docker-compose exec backend pytest apps/accounts/tests/ -v

# Run with coverage
docker-compose exec backend pytest --cov=apps --cov-report=term-missing
```

## Expected Test Coverage Areas

- **Registration**: success, duplicate email, weak password, invitation token linking
- **Login**: correct credentials, wrong password, disabled user, suspended tenant, remember-me token expiry
- **Token**: refresh flow, expired token, invalid token
- **Tenant isolation**: user from tenant A cannot access tenant B data
- **Invitations**: create, list, cancel, accept, expired token
- **Members**: list, role change, remove, last admin protection
- **Password reset**: request, confirm, invalid token
