# API Contracts: Authentication

**Base URL**: `/api/v1/auth/`

All request/response bodies are JSON. All protected endpoints require `Authorization: Bearer <access_token>` header.

---

## POST /api/v1/auth/register

Register a new user and create their tenant simultaneously.

### Request

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "company_name": "My Business Inc."
}
```

### Response — 201 Created

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": null,
    "status": "active"
  },
  "tenant": {
    "id": "uuid",
    "name": "My Business Inc.",
    "status": "active"
  }
}
```

### Response — 400 Bad Request

```json
{
  "email": ["user with this email already exists."],
  "password": ["This password is too short."]
}
```

---

## POST /api/v1/auth/login

Authenticate with email and password.

### Request

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "remember_me": false
}
```

### Response — 200 OK (single tenant)

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "John Doe",
    "status": "active"
  },
  "tenants": [
    {
      "id": "uuid",
      "name": "My Business Inc.",
      "role": "admin"
    }
  ],
  "active_tenant": {
    "id": "uuid",
    "name": "My Business Inc.",
    "role": "admin"
  }
}
```

### Response — 200 OK (multiple tenants, need selection)

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": { "...same..." },
  "tenants": [
    { "id": "uuid1", "name": "Business A", "role": "admin" },
    { "id": "uuid2", "name": "Business B", "role": "accountant" }
  ],
  "active_tenant": null
}
```

### Response — 401 Unauthorized

```json
{
  "detail": "Invalid email or password."
}
```

### Response — 403 Forbidden (disabled user)

```json
{
  "detail": "Account has been disabled. Contact your administrator."
}
```

---

## POST /api/v1/auth/logout

Invalidate the current refresh token.

### Request

```json
{
  "refresh": "<jwt_refresh_token>"
}
```

### Response — 205 Reset Content

*(No body)*

---

## POST /api/v1/auth/refresh

Obtain a new access token using a refresh token.

### Request

```json
{
  "refresh": "<jwt_refresh_token>"
}
```

### Response — 200 OK

```json
{
  "access": "<new_jwt_access_token>"
}
```

---

## POST /api/v1/auth/password-reset/request

Request a password reset email.

### Request

```json
{
  "email": "user@example.com"
}
```

### Response — 204 No Content

*(Always returns 204 regardless of whether email exists, to prevent email enumeration)*

---

## POST /api/v1/auth/password-reset/confirm

Reset password using the token from the email.

### Request

```json
{
  "token": "<reset_token>",
  "password": "newSecurePassword456"
}
```

### Response — 200 OK

```json
{
  "detail": "Password has been reset successfully."
}
```

---

## GET /api/v1/auth/me

Get the authenticated user's profile.

### Headers

`Authorization: Bearer <access_token>`
`X-Tenant-ID: <tenant_id>`

### Response — 200 OK

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "status": "active",
  "created_at": "2026-06-13T10:00:00Z"
}
```

---

## PATCH /api/v1/auth/me

Update the authenticated user's profile.

### Headers

`Authorization: Bearer <access_token>`
`X-Tenant-ID: <tenant_id>`

### Request

```json
{
  "display_name": "John Updated"
}
```

### Response — 200 OK

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Updated",
  "status": "active"
}
```
