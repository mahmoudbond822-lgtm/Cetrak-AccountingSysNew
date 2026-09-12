# Data Model: 012-H Production Hardening

Only one new table is introduced by the hardening phase. All pre-existing tables are unchanged (the accounting report fixes were compute-layer only).

## `core_audit_log` — Immutable audit trail (constitution §II)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `uuid4`, not editable |
| `tenant_id` | FK `core.Tenant` | `SET_NULL`, nullable, indexed; tenant scope |
| `actor_id` | FK `accounts.User` | `SET_NULL`, nullable, `related_name="+"` |
| `action` | `CharField(100)` | indexed; e.g. `sales.invoice.post` |
| `target_type` | `CharField(64)` | `"<app_label>.<model_name>"`, blankable |
| `target_id` | `CharField(64)` | indexed, blankable (model PK as string) |
| `before_data` | `JSONField` | sanitized snapshot before the mutation |
| `after_data` | `JSONField` | sanitized snapshot after the mutation |
| `metadata` | `JSONField` | request path/method/IP/user-agent (from request context) |
| `created_at` | `DateTimeField` | `auto_now_add`, indexed; effective `timestamp` |

### Immutability guards (application layer)

- `AuditLog.save()`: raises `ValueError` when `pk is not None and not self._state.adding` (no UPDATE path).
- `AuditLog.delete()`: raises `TypeError`.
- `AuditLogQuerySet.update()` / `.delete()`: raise `TypeError` (no bulk mutation).
- No viewset/URL exposes audit rows — creation happens exclusively through `AuditService.record` from the service layer; there is no read API in scope.
- Database-level protection (e.g., a SQL trigger or revoked UPDATE/DELETE grants) is deliberately **not** introduced — documented as a known limitation; the app-layer guards plus absence of any write endpoint are the enforced boundary.

### Write mechanics

- `AuditService.record(action, *, tenant_id, target, actor, before, after, metadata)` is the single entry point (services layer only).
- Actor/tenant/metadata come from the thread-local request context set by `BlacklistCheckingJWTAuth.authenticate` (from the validated token) and cleared by middleware; explicit `actor`/`tenant_id` arguments override when meaningful (e.g. `auth.register`).
- A recursive `_sanitize` normalizes `Decimal`/`UUID`/`datetime` to JSON-safe strings and **drops any key** containing `password` / `refresh` / `access` / `token` / `secret` / `authorization` / `api_key` / `session`.

## No other schema changes

P1-1/P1-2/P1-5 (report filtering, balance-sheet clamping removal, Decimal math) are compute-layer only — no migrations.
P1-7 (status enforcement) reuses existing `User.status` / `Tenant.status` columns — no migrations.
P1-3/P1-4 are frontend-only — no migrations.

Migration check: `py manage.py makemigrations --check --dry-run` → **"No changes detected"**.