# Implementation Plan: AUD-025 — bcrypt Password Hashing

**Branch**: current | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

## Summary

Make bcrypt the active password hashing algorithm to satisfy constitution §VI, eliminate the
MD5 test-only hasher, and enable transparent upgrade of existing PBKDF2 hashes on login —
with zero API, JWT, or UX change and no forced resets.

## Current State (verified this session)

- Django `6.0.4`; `bcrypt 5.0.0` installed; `base.py` has **no** `PASSWORD_HASHERS` (→ Django
  default PBKDF2 first); `test.py` forces `MD5PasswordHasher`.
- `requirements/base.txt` already declares `bcrypt>=4.0,<5.0` — no dependency change required.
- `AuthService.login` (line 75) calls low-level `hashers.check_password` → legacy hashes never
  upgrade.
- Serializers never expose `password`; registration uses `UserManager.create_user` →
  `set_password` (standard Django hashing).

## Steps

### Step 1 — Configure the hasher list (base.py)

Add to `backend/config/settings/base.py`:

```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
```

- `BCryptSHA256PasswordHasher` first → all **new** passwords are `bcrypt_sha256$` (cost 12).
- PBKDF2 entries keep every existing `pbkdf2_sha256$` / `pbkdf2_sha1$` hash verifiable.
- `MD5PasswordHasher` last mirrors Django's own legacy verification fallback; it can never be
  selected when encoding a new password.

### Step 2 — Remove the MD5 test override (test.py)

Delete the `PASSWORD_HASHERS = ["…MD5PasswordHasher"]` block from
`backend/config/settings/test.py` so tests run on the real bcrypt-first configuration.

Expected consequence: the backend suite gets slower (bcrypt cost 12). Accepted — the MD5
override is the documented insecure-deviation AUD-025 removes, and the constitution forbids
weakening parameters for test speed (spec §Security Constraints).

### Step 3 — Enable automatic hash upgrade (services.py)

In `AuthService.login`, replace:

```python
if not check_password(password, user.password):
```

with Django's standard per-user verification:

```python
if not user.check_password(password):
```

and drop the `from django.contrib.auth.hashers import check_password` import. `user.check_password`
re-encodes the stored hash with the primary hasher on success (lazy upgrade). This is the only
auth-code change; it does not alter the API, errors, or JWT flow.

### Step 4 — Remove the stray debug script

Delete `backend/check_user.py` (tracked but unused; hard-codes a credential and calls the
low-level check path). Security-review cleanup under AUD-025.

### Step 5 — Tests

Add `backend/apps/accounts/tests/test_password_hashing.py` covering spec §Testing Requirements:
hash storage, bcrypt ident, correct/wrong auth, serializer non-exposure, configured-hasher
usage, PBKDF2-compat login, and automatic PBKDF2→bcrypt upgrade on login.

### Step 6 — Verification

- Targeted: `py -m pytest apps/accounts/tests/test_password_hashing.py -q`
- Full: `py -m pytest apps/ -q`
- Migrations: `py manage.py makemigrations --check --dry-run`
- Frontend: untouched (auth API/UI unchanged); no build required.

## Gates

Tenant isolation, API contract, JWT, standards, security, performance, MVP discipline all pass;
no constitution violation — this change removes the §VI deviation.

## Constitution Check

Satisfies §VI ("Passwords MUST be hashed with bcrypt"). No other principle affected.