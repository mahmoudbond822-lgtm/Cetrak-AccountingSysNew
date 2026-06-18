# Research: Multi-Tenancy Hardening

**Phase**: 0 — Research & Unknown Resolution

**Date**: 2026-06-18

## Decisions

### 1. Middleware JWT parsing timing

**Decision**: The middleware reads `request.auth` (populated by DRF's `JWTAuthentication` via `BlacklistCheckingJWTAuth`). DRF authentication runs during view processing, which is *after* middleware. However, the `process_request` hook runs before the view. This means `request.auth` is not yet available in the middleware.

**Solution**: The middleware parses the `Authorization` header directly to extract the JWT and read its `tenant_id` claim, rather than relying on `request.auth`.

**Rationale**: Django middleware processes requests before DRF's authentication runs. `request.auth` is only available in views and DRF's authentication classes. The middleware must implement its own lightweight JWT decoding (without signature validation — that's the auth class's job — just claim extraction).

**Alternatives considered**:
- Moving tenant validation to DRF authentication class: violates separation of concerns (auth ≠ tenant resolution)
- Using `process_view` instead of `process_request`: would work but `process_view` is Django-specific, not universal middleware

### 2. Django's `process_request` vs `process_view`

**Decision**: Use `process_request` with manual JWT parsing.

**Rationale**: `process_request` runs on every request and can return an `HttpResponseForbidden` early. Manual JWT parsing (split by `.`, base64-decode the payload) is safe because the middleware only reads claims — it does NOT validate the signature. Signature validation is deferred to the DRF auth class.

**Alternatives considered**:
- Using `process_view` to access `request.auth` post-authentication: couples middleware to DRF's lifecycle, less portable

### 3. Membership validation query cost

**Decision**: The middleware runs one `Membership.objects.filter(user=request.user, tenant_id=...).exists()` query per request. This is acceptable because:
- The query is on indexed columns (user_id covered by unique constraint, tenant_id getting an index)
- At 50 users/tenant and typical request rates (<100 req/s), this adds <1ms per request
- The alternative (no validation) introduces data leak risk that no performance optimization justifies

**Rationale**: Security (Constitution Article VI) > micro-optimization. If profiling shows this becomes a bottleneck in the future, a cache layer can be added.

## Key Findings

- `TenantScopedModel.tenant` with `null=True` allows orphan records — confirmed by examining the Invitation migration (`0003_invitation.py:27`)
- `Membership.tenant_id` has no dedicated index — only the composite `(user, tenant)` unique constraint exists, which cannot efficiently serve `WHERE tenant_id = X` alone
- `BlacklistCheckingJWTAuth` in `auth.py` extends `JWTAuthentication` and runs during view processing, not during middleware
- `request.auth` is set by DRF's `authenticate()` method, which is called by the `AuthenticationMiddleware` counterpart in DRF's `APIView` dispatch flow
- All 6 views that use `request.tenant_id` receive it already as a raw string from the current passive middleware — converting to UUID in the middleware simplifies downstream code
- No existing test directly depends on the passive middleware behavior, so the middleware rewrite should not break existing tests
