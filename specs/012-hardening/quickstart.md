# Validation Scenarios: 012-H Production Hardening

Backend scenarios are fully covered by automated regression tests (`324 passed, 1 skipped`). This file documents the **manual** verification for the two frontend-only fixes (P1-3 refresh rotation, P1-4 invoice modal) — the repository has no UI test harness, so these are the strongest practical checks available.

## P1-3 — Refresh token rotation (manual)

Setup: `docker compose -f infra/docker-compose.yml up` (or a dev server), then log in as a user.

1. **Rotation persists both tokens.** Open DevTools → Application → Local Storage. Trigger any silent-refresh path (or wait past the access-token lifetime) and confirm:
   - `accessToken` is replaced, and
   - `refreshToken` is **also replaced** with a new value different from the previous one.
   - The session continues; **no redirect to `/login`** occurs.
2. **Old rotated refresh is not reused.** After a refresh, the stored `refreshToken` value must equal the newest backend response (`GET /refresh/` returns `refresh`).
3. **Retry succeeds.** With two browser tabs open and an expired access token, hit a protected endpoint in each tab nearly simultaneously. Exactly one refresh request should be observable in the Network tab **(single-flight)**; both tabs' original requests succeed with the new access token.
4. **Genuine failure logs out.** In the refresh endpoint response (or via the Authorization header of `/auth/refresh/`), force a rejection (e.g., invalidate the stored refresh token in Local Storage, or suspend the tenant). The next protected request must clear storage and land on `/login`.

## P1-4 — Invoice modal reset (manual)

1. **Create** invoice A (`+ New Invoice`), fill fields, save.
2. **Edit** invoice A — confirm all fields open pre-populated; save.
3. **Close** the modal.
4. **Edit** invoice B — confirm the modal opens with **B's** data (not A's, not blank).
5. **Save** B — confirm B's record is stored intact with B's values.
6. **Round trip**: edit A, close, edit B, close, edit A again — each open must show that record's own data.
7. Repeat the same sequence from the **Create** button after an edit (create → edit → create) to confirm the "new" form is always blank on open.

Any regression on steps 4–7 (stale/blank fields overwriting the target record) indicates the remount `key` is ineffective.

## P1-1 — Journal Draft → Post (manual)

1. Journal screen → **+ New Entry** → the form's primary action is **Save Draft**.
2. Create a balanced entry; it lists with a **Draft** badge. The Ledger and the three reports must **not** include it.
3. Click **Post** on the row; badge flips to **Posted**; the entry now appears in Ledger, Trial Balance, Income Statement, and Balance Sheet.
4. A re-Post attempt and any edit/delete of the posted entry is rejected.

## P1-6 / P1-7 — quick sanitization checks (service/API level)

- Disable a logged-in user's `status` (DB) → their next request is rejected immediately (401), and `/tenants/switch/` also fails.
- Set a tenant to `Suspended`/`Cancelled` (DB) → all requests scoped to that tenant return 403 and switch refuses entry.
- Audit rows are visible only in the `core_audit_log` table and cannot be updated or deleted via Django ORM (`AuditLog.objects.update/delete` raise `TypeError`).