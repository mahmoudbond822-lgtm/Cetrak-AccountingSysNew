# Feature Specification: AUD-025 — bcrypt Password Hashing

**Feature**: AUD-025 bcrypt password hashing hardening
**Created**: 2026-09-21
**Status**: Draft

## Problem Statement

The project constitution (§VI) requires that "Passwords MUST be hashed with bcrypt."
Today the repository does not satisfy this requirement in production **or** in tests:

1. **Production/dev (base.py):** no `PASSWORD_HASHERS` is declared, so Django applies its
   default `PBKDF2PasswordHasher` first. Passwords are salted and hashed (never plaintext),
   but the mandated bcrypt algorithm is not used for new hashes.
2. **Tests (test.py):** `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]`
   deliberately weakens hashing for speed. MD5 is a broken cryptographic primitive; using it
   as the *only* test hasher means the auth test suite exercises a hashing path that will never
   run in production, leaving real hashing behavior unverified. This was recorded as a known
   deviation in `docs/audits/production-readiness-audit-001.md` (AUD-025) and re-verified as
   still open in audits 003 and the H2 hardening report.
3. **bcrypt dependency:** `backend/requirements/base.txt` already declares `bcrypt>=4.0,<5.0`
   and the environment has bcrypt installed, but the hasher is never configured, so the
   dependency is dead weight and Django's bcrypt hashers are never used.
4. **Hash upgrading:** `AuthService.login` (`accounts/services.py:75`) calls the low-level
   `django.contrib.auth.hashers.check_password(password, user.password)` directly. That does
   verify legacy hashes, but it never re-encodes them. Even after bcrypt is made the primary
   hasher, existing PBKDF2 hashes would never be upgraded to bcrypt on login.

## Security Objective

Eliminate every insecure or inconsistent password-hashing configuration, make bcrypt the
active algorithm for all new and upgraded passwords, keep all existing valid hashes verifiable,
and do all of this without changing the public authentication API, the JWT flow, or requiring
users to reset passwords.

## Current Behavior

- New passwords: hashed with PBKDF2 (cost via Django default) in dev/prod; MD5 in tests.
- Password verification: `check_password(password, user.password)` in `AuthService.login`,
  with `User.check_password` used only by stray scripts.
- Hash upgrading on login: **none** (the raw `check_password` call never re-hashes).
- Password exposure: not exposed by serializers (`UserSerializer` fields are id/email/
  display_name/status; `RegisterSerializer.password` and `LoginSerializer.password` are
  `write_only` / input-only).
- Plaintext storage: none. `UserManager.create_user` → `user.set_password(password)` (Django
  standard hashing), used by registration, invitation acceptance, and tests.
- JWT: simplejwt `BlacklistCheckingJWTAuth`; password hashing is unrelated to JWT issuance.

## Target Behavior

- `base.py` declares `PASSWORD_HASHERS` with **`BCryptSHA256PasswordHasher` first** and the
  PBKDF2 family retained so legacy hashes remain verifiable; salted-MD5 retained last purely
  as a legacy *verification* fallback (mirrors Django's own default list).
- `test.py` removes the MD5 override so the full auth suite runs against the real, production
  bcrypt-first hasher configuration.
- `AuthService.login` verifies via Django's standard `user.check_password(password)`, which
  **automatically re-encodes** an older-format hash with the primary bcrypt hasher on success.
- No new custom crypto, no manual salt generation, no weakened parameters.

## Password Hashing Algorithm

- Primary: Django `BCryptSHA256PasswordHasher` (`bcrypt_sha256$…`), bcrypt cost factor 12
  (Django 6.0 default). SHA-256 pre-hashing avoids the bcrypt 72-byte truncation edge case.
- Fallback (verification only): `PBKDF2PasswordHasher`, `PBKDF2SHA1PasswordHasher`,
  `MD5PasswordHasher` — mirroring Django's own default ordering but with bcrypt promoted first.
- Requires the existing `bcrypt` package (already declared in `requirements/base.txt`).

## Compatibility Expectations

- Every existing valid hash of any form still in `PASSWORD_HASHERS` remains verifiable:
  PBKDF2-SHA256 (`pbkdf2_sha256$`), PBKDF2-SHA1 (`pbkdf2_sha1$`), unsalted/django-MD5
  (`md5$`) remain supported; bcrypt (`bcrypt$` / `bcrypt_sha256$`) checks are supported by
  Django's standard `check_password`.
- No user is forced into a password reset; nobody must change passwords because of this change.
- The authentication API is unchanged: `/auth/register`, `/auth/login`, `/auth/refresh`,
  `/auth/logout`, `/auth/me`, tenant switch, and invitation flows keep their exact request and
  response contracts. JWT issuance/validation is untouched.

## Migration / Upgrade Behavior

- **No data migration.** Existing rows are left in place; changing the hasher list alone does
  not touch stored hashes.
- **Lazy upgrade:** after a successful login, a user whose stored hash algorithm is not the
  primary bcrypt hasher is transparently re-hashed to bcrypt and the `password` column is
  updated in the same request (Django `User.check_password` behavior). This is verified by a
  dedicated test. If verification is not supported for an orphan format, that is documented,
  not invented — no custom migration is created.

## API Compatibility

- No request/response shape changes. Passwords never appear in responses: registration/login
  responses carry access token, user, tenant payloads only; `UserSerializer` and
  `MemberSerializer` do not include `password`.
- Rate limits, CSRF, refresh-cookie, blacklist behavior unchanged.

## Security Constraints

- Passwords never stored in plaintext.
- Passwords never logged (login errors return the generic "Invalid email or password.").
- No custom cryptographic code, no manual salt handling, no parameter weakening for speed.
- Do not lower the bcrypt cost factor in tests or anywhere else.

## Testing Requirements

1. New password stored as a hash (not equal to plaintext).
2. Stored hash identifies the expected algorithm (`bcrypt_sha256$`).
3. Correct password authenticates; wrong password fails with 401.
4. Password/hash never appears in serializer or auth response output.
5. Registration and `create_user` use the configured primary hasher.
6. A stored PBKDF2 hash remains verifiable via the login endpoint.
7. After a successful login with a PBKDF2 hash, the stored hash is upgraded to `bcrypt_sha256$`
   (automatic upgrade verified, not assumed).
8. Agent-created users (test `create_user` paths) continue to authenticate.
9. The complete existing backend suite (auth, JWT, tenant-switch, invitation-binding,
   accounting, inventory, sales, purchases) still passes with the bcrypt-first config.
10. `makemigrations --check` reports no changes.

## Acceptance Criteria

- [ ] `PASSWORD_HASHERS` explicitly configured in `base.py` with bcrypt first.
- [ ] `test.py` no longer overrides the hasher list to MD5.
- [ ] `AuthService.login` uses Django's `user.check_password` so legacy hashes upgrade.
- [ ] No plaintext password storage anywhere.
- [ ] Existing supported hashes (PBKDF2, etc.) remain verifiable.
- [ ] Existing users authenticate without a forced reset.
- [ ] JWT behavior unchanged.
- [ ] Serializers never expose `password`.
- [ ] New hashing/config tests pass; whole backend suite passes.
- [ ] No unrelated behavior changed (working tree contains only AUD-025 changes).

## Explicit Non-Goals

- Not AUD-026 (Celery). Not AUD-010/11/12/15/19/23/27/29.
- No redesign of the authentication flow, JWT, cookies, CSRF, rate limiting, or user model.
- No custom password-hashing utilities; no migration of stored hashes; no forced reset flows.
- No Argon2 adoption, no scrypt promotion, no reordering of dependence on the constitution's
  §VII async requirements.
- No dependency upgrade or broad requirements refresh; the existing `bcrypt` pin stays.