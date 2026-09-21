# AUD-025 — bcrypt Password Hashing: Tasks

Each task is independently verifiable. Status reflects the implementation session.

## Config

- [x] T1. `base.py` declares `PASSWORD_HASHERS` with `BCryptSHA256PasswordHasher` first.
      Verify: `settings.PASSWORD_HASHERS[0]` is the bcrypt sha256 hasher name.
- [x] T2. PBKDF2 (+SHA1) and MD5 hashers retained after bcrypt in the list.
      Verify: list contains them in order.
- [x] T3. `test.py` no longer sets `PASSWORD_HASHERS` to MD5.
      Verify: `get_hashers()[0].algorithm == "bcrypt_sha256"` under test settings.

## Auth behavior

- [x] T4. `AuthService.login` verifies via `user.check_password(password)`.
      Verify: code inspection + login tests pass.
- [x] T5. Raw `hashers.check_password` import removed from services if unused.
      Verify: `grep check_password apps/accounts/services.py` only shows `user.check_password`.
- [x] T6. Stray `backend/check_user.py` deleted.
      Verify: file absent from working tree.

## Tests (new `apps/accounts/tests/test_password_hashing.py`)

- [x] T7. New/registered password stored as hash ≠ plaintext and starts `bcrypt_sha256$`.
- [x] T8. `identify_hasher(stored).algorithm == "bcrypt_sha256"`.
- [x] T9. Correct password logs in (200); wrong password returns 401.
- [x] T10. `password`/hash absent from register, login, and `/auth/me/` payloads and from
      `UserSerializer`/`MemberSerializer` output.
- [x] T11. Registration and `create_user` store hashes using the configured primary hasher.
- [x] T12. A user seeded with a `PBKDF2PasswordHasher` hash logs in successfully (compat).
- [x] T13. After successful login of that PBKDF2 user, stored hash is upgraded to `bcrypt_sha256$`
      (automatic upgrade verified, not assumed).
- [x] T14. Existing auth/JWT test suites still pass unchanged.

## Verification

- [x] T15. `py -m pytest apps/ -q` — full suite passes.
- [x] T16. `py manage.py makemigrations --check --dry-run` — "No changes detected".
- [x] T17. `git status --short` — only AUD-025 files present (config, services, tests, spec docs,
      deleted `check_user.py`).

## Docs

- [x] T18. `specs/025-bcrypt/{spec.md,plan.md,tasks.md}` present.
- [x] T19. `report.md` written summarizing implementation, security review, and results.