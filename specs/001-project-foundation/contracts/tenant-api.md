# API Contracts: Tenant & Team Management

**Base URL**: `/api/v1/tenants/`

All endpoints require `Authorization: Bearer <access_token>` and `X-Tenant-ID: <tenant_id>` headers.

---

## GET /api/v1/tenants/current

Get the currently active tenant's details.

### Response — 200 OK

```json
{
  "id": "uuid",
  "name": "My Business Inc.",
  "status": "active",
  "member_count": 3,
  "created_at": "2026-06-13T10:00:00Z"
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

## POST /api/v1/tenants/invitations

Invite a new member to the tenant. Admin only.

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
  "expires_at": "2026-06-20T10:00:00Z"
}
```

---

## GET /api/v1/tenants/invitations

List pending invitations. Admin only.

### Response — 200 OK

```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid",
      "email": "newmember@example.com",
      "role": "accountant",
      "expires_at": "2026-06-20T10:00:00Z",
      "status": "pending"
    }
  ]
}
```

---

## DELETE /api/v1/tenants/invitations/{id}

Cancel a pending invitation. Admin only.

### Response — 204 No Content

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

---

## PATCH /api/v1/tenants/members/{user_id}/role

Change a member's role. Admin only. Cannot change the last admin's role.

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

---

## DELETE /api/v1/tenants/members/{user_id}

Remove a member from the tenant. Admin only. Cannot remove the last admin.

### Response — 204 No Content
