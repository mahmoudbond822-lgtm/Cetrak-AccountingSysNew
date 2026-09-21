# AUD-025 — bcrypt Password Hashing: Implementation Report

**Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Tasks**: [tasks.md](./tasks.md)

## Current Authentication State

- JWT-based authentication (simplejwt, `BlacklistCheckingJWTAuth`) with a blacklist model and
  user-status enforcement — **unchanged**. The `/auth/register`, `/auth/login`, `/auth/refresh`,
  `/auth/logout`, `/auth/me`, tenant-switch, and invitation flows keep identical contracts.
- Before this change, passwords were hashed with Django's default **PBKDF2** in dev/prod and
  **MD5** in the test configuration (`test.py`), and the mandated `bcrypt` dependency sat unused.
- After this change, **bcrypt** (`BCryptSHA256PasswordHasher`, cost factor 12, salted by Django)
  is the active algorithm for every new and upgraded password in all environments, including
  tests.

## Implementation

| File | Change |
| --- | --- |
| `backend/config/settings/base.py` | Added explicit `PASSWORD_HASHERS`: `BCryptSHA256PasswordHasher` first; `PBKDF2PasswordHasher`, `PBKDF2SHA1PasswordHasher`, `MD5PasswordHasher` retained as verification fallbacks (mirrors Django's own legacy list, bcrypt promoted). |
| `backend/config/settings/test.py` | Removed the MD5-only `PASSWORD_HASHERS` override — tests now run on the real bcrypt-first configuration. |
| `backend/apps/accounts/services.py` | `AuthService.login` now verifies with Django's standard `user.check_password(password)` (removed the low-level `hashers.check_password` import), enabling automatic re-hash of legacy formats on success. |
| `backend/apps/accounts/tests/test_password_hashing.py` | New: 15 tests covering hashing, auth, serializer non-exposure, configured-hasher usage, PBKDF2 compatibility, and automatic upgrade. |
| `backend/check_user.py` | Deleted — tracked stray debug script (hard-coded `admin@example.com` / `AdminPass123`). |
| `specs/025-bcrypt/` | spec.md, plan.md, tasks.md, report.md. |

## Security

- Hashes: stored via Django `set_password`/`make_password` with Salted bcrypt (`bcrypt_sha256$`,
  cost 12). No plaintext storage anywhere; no manual salts; no custom crypto.
- Serializers: `UserSerializer` and `MemberSerializer` exclude `password`; `RegisterSerializer`
  and `LoginSerializer.password` are input-only; register/login/`me` payloads are password-free
  (tested).
- Logging/audit: login errors are generic ("Invalid email or password."); `apps/core/audit.py`
  redacts `password` in the `_SENSITIVE_KEYS` set.
- Legacy hashes: all previously supported formats (PBKDF2-SHA256, PBKDF2-SHA1, Django salted
  MD5) remain verifiable; no forced resets; existing users authenticate as before.
- Auto-upgrade: on the next successful login a legacy PBKDF2 hash is transparently re-encoded to
  bcrypt (verified by test).
- NOT addressed (pre-existing, out of scope — flagged for follow-up): `backend/debug_account.py`
  is another stray debug script containing a hard-coded test credential
  (`admin@test.com`/`Pass1234`) and was intentionally left in place to keep this diff scoped to
  AUD-025. `requirements/base.txt` pins `bcrypt>=4.0,<5.0` while the environment has 5.0.0
  installed; both satisfy Django's bcrypt adapapter (`>=3.1`), so the pin was left unchanged
  (no dependency refresh under spec constraint).

## Tests

- New: `apps/accounts/tests/test_password_hashing.py` — **15 passed** (10.8 s).
- Full backend suite under `config.settings.test`: **436 passed, 1 skipped** (up from the 421
  baseline; +15 new). Runtime increased from MD5-fast to **~5 min 13 s** — the honest bcrypt
  cost, per constitution §VI and the no-test-weakening constraint; the cost factor was not
  lowered anywhere.
- Migrations: `py manage.py makemigrations --check --dry-run` → "No changes detected".
- Frontend: not touched (no API/UI/auth behavior change).

## Spec-Kit

- `specs/025-bcrypt/spec.md` — problem, security objective, current/target behavior, algorithm,
  compatibility, migration/upgrade, API compat, security constraints, testing requirements,
  acceptance criteria, non-goals.
- `specs/025-bcrypt/plan.md`, `specs/025-bcrypt/tasks.md` (all checked), `report.md`.

## Git

- Commit: `fix(auth): harden password hashing with bcrypt`
- Files staged: backend config/settings, accounts/services.py, accounts tests, deleted
  check_user.py, specs/025-bcrypt. Nothing pushed.