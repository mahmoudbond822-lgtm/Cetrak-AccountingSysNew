# API Contracts: Team Management

**Base URL**: `/api/v1/tenants/`

All endpoints require `Authorization: Bearer <access_token>` and `X-Tenant-ID: <tenant_id>` headers. Admin role required unless noted.

---

## POST /api/v1/tenants/invitations

Create a new invitation for a team member. Admin only.

### Request

```json
{
  "email": "newmember@example.com",
  "role": "accountant"
}
```

### Response — 201 Created

```json
{
  "id": "uuid",
  "email": "newmember@example.com",
  "role": "accountant",
  "expires_at": "2026-06-21T10:00:00Z",
  "status": "pending"
}
```

### Response — 400 Bad Request

```json
{
  "email": ["user with this email already has a pending invitation."]
}
```

### Response — 403 Forbidden (non-admin user)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

## GET /api/v1/tenants/invitations

List pending invitations for the current tenant. Admin only.

### Response — 200 OK

```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "email": "newmember@example.com",
      "role": "accountant",
      "expires_at": "2026-06-21T10:00:00Z",
      "status": "pending"
    }
  ]
}
```

---

## DELETE /api/v1/tenants/invitations/{id}

Cancel a pending invitation. Admin only.

### Response — 204 No Content

*(No body)*

### Response — 404 Not Found

```json
{
  "detail": "Invitation not found."
}
```

---

## GET /api/v1/tenants/members

List all members of the current tenant. Admin only.

### Response — 200 OK

```json
{
  "count": 3,
  "results": [
    {
      "user_id": "uuid",
      "email": "admin@example.com",
      "display_name": "John Admin",
      "role": "admin",
      "status": "active",
      "joined_at": "2026-06-13T10:00:00Z"
    },
    {
      "user_id": "uuid",
      "email": "accountant@example.com",
      "display_name": "Jane CPA",
      "role": "accountant",
      "status": "active",
      "joined_at": "2026-06-14T09:00:00Z"
    }
  ]
}
```

---

## PATCH /api/v1/tenants/members/{user_id}/role

Change a member's role. Admin only.

### Request

```json
{
  "role": "manager"
}
```

### Response — 200 OK

```json
{
  "user_id": "uuid",
  "email": "member@example.com",
  "role": "manager",
  "status": "active"
}
```

### Response — 400 Bad Request (last admin protection)

```json
{
  "detail": "Cannot change the role of the last admin. Assign another admin first."
}
```

---

## DELETE /api/v1/tenants/members/{user_id}

Remove a member from the tenant. Admin only.

### Response — 204 No Content

### Response — 400 Bad Request (last admin protection)

```json
{
  "detail": "Cannot remove the last admin. Assign another admin first."
}
```

---

## POST /api/v1/auth/register (modified)

Modified to accept optional `invitation_token` parameter.

### Request (new user with invitation)

```json
{
  "email": "newmember@example.com",
  "password": "securePassword123",
  "company_name": "My Business Inc.",
  "invitation_token": "<invitation_token>"
}
```

### Behavior

- If `invitation_token` is provided and valid: user is created, auto-linked to the inviting tenant with the invitation's role, and no new tenant is created.
- If `invitation_token` is provided and invalid/expired: registration is rejected with 400 error.
- If `invitation_token` is not provided: standard flow (create user + tenant + admin membership).

### Response — 201 Created (with invitation)

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": "uuid",
    "email": "newmember@example.com",
    "display_name": null,
    "status": "active"
  },
  "tenants": [
    {
      "id": "uuid",
      "name": "Inviting Company",
      "role": "accountant"
    }
  ],
  "active_tenant": {
    "id": "uuid",
    "name": "Inviting Company",
    "role": "accountant"
  }
}
```

---

## POST /api/v1/tenants/switch/{tenant_id}

Switch the active tenant for the current session.

### Response — 200 OK

```json
{
  "access": "<new_jwt_access_token_with_updated_tenant_claim>",
  "tenant": {
    "id": "uuid",
    "name": "Business B",
    "role": "accountant"
  }
}
```
