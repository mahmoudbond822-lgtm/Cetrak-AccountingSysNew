# Middleware Error Contracts

**Phase**: 1 — Design

**Date**: 2026-06-18

## Error Responses

All middleware-generated error responses use the existing `{"detail": "..."}` format to match the rest of the API.

### Invalid Tenant ID Format

Returned when the `X-TENANT-ID` header value or JWT `tenant_id` claim is not a valid UUID.

```json
HTTP 403 Forbidden

{
    "detail": "Invalid tenant ID format."
}
```

### No Membership

Returned when the authenticated user does not have an active membership for the resolved tenant.

```json
HTTP 403 Forbidden

{
    "detail": "You do not have access to this tenant."
}
```

### No Tenant Context

Returned when the request is authenticated but neither the JWT nor the `X-TENANT-ID` header provides a tenant identifier.

```json
HTTP 403 Forbidden

{
    "detail": "No tenant context provided. Specify a tenant ID via X-TENANT-ID header or your JWT."
}
```

## Allowed Paths (no tenant enforcement)

The following paths are exempt from tenant enforcement because they are unauthenticated or handle tenant context setup:

| Path | Method | Reason |
|------|--------|--------|
| `/api/v1/auth/register/` | POST | User may not have tenant context yet |
| `/api/v1/auth/login/` | POST | User not yet authenticated |
| `/api/v1/auth/refresh/` | POST | Token refresh may happen without active session |
| `/api/v1/auth/logout/` | POST | Logout should work without tenant context |
| `/api/v1/tenants/switch/{id}/` | POST | This endpoint changes the tenant context itself |
