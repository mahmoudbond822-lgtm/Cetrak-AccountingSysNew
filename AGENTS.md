<!-- SPECKIT START -->
Current phase: WORKING TREE CLEAN — all completed streams are committed. Visual QA complete.

1. **`specs/014-auto-journal-entry-code`** — auto-assigned journal entry references (**committed**). Backend mints
   `JE-YYYY-NNNN` per tenant per year at save (`JournalEntryService.next_reference()`, collision-skip,
   max-suffix); serializer accepts blank/missing reference; read-only preview endpoint
   `GET /accounting/journal-entries/next-reference/`; the create form shows a disabled preview and omits
   the reference from the payload. Entries stay immutable (405 on PUT/PATCH/DELETE). Report:
   `specs/014-auto-journal-entry-code/report.md` (all tasks checked in `tasks.md`).
   Note: `specs/014-auto-journal-entry/` was a **superseded** draft (original `JE-0001` format) and has been
   removed at closeout; the authoritative journal spec is `014-auto-journal-entry-code`.
2. **Frontend design system v1** (**committed**) — `docs/specs/frontend-design-system-v1.md` (+ audit +
   implementation + visual-qa doc). Tokenized, dark-mode-aware system: `styles/tokens.css` + `globals.css`
   + `lib/tokens.js`; 31 exports from `components/ui/`; `AppShell`/`Sidebar`/`TopBar` replacing `AppLayout` +
   the four sub-navs; dead duplicate components deleted; 12 `window.confirm` → `ConfirmDialog`, 11 `alert()` →
   Toast. **Zero backend / API / payload / auth-behavior change** (`services/api.js` untouched).
3. **`specs/025-bcrypt`** — bcrypt password hashing (**committed**). `PASSWORD_HASHERS` bcrypt-first in
   `base.py`; MD5 test override removed; `AuthService.login` uses `user.check_password` (lazy PBKDF2→bcrypt
   upgrade). Report: `specs/025-bcrypt/report.md`.
4. **`specs/026-celery`** — Celery background-task foundation (**committed**, closes AUD-026). All Celery
   config moved to `base.py` (env-driven `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` with local-only defaults,
   JSON-only serialization/accept content, UTC timezone, broker retry on startup); dev/local/prod inherit it;
   eager mode confined to `test.py` (with a base-settings guard test); `apps/core/tasks.py` registers the
   `core.ping` infrastructure proof task (§VII now has a real execution path); dead `accounts/tasks.py`
   re-export removed; `backend/.env.example` documents the broker convention (`.env` stays gitignored).
   Opt-in real-broker integration test gated on `CETRAK_CELERY_INTEGRATION=1`. No accounting/auth/API/
   frontend/deployment change; `config/celery.py` untouched. Report: `specs/026-celery/report.md`.
5. **AUD-015 email delivery** (**committed**) — `core/mail.py` + Celery-backed `send_email` task,
   invitation email templates, env-driven email config in `base.py`/`prod.py`/`.env.example`/`render.yaml`.
   First real consumer of the AUD-026 Celery substrate. Report: `docs/audits/AUD-015-implementation-report.md`.
6. **AUD-029 list pagination + invoice N+1** (**committed**) — `apps/core/pagination.py`
   (`DefaultPagination`: 25/page, `?page_size=` capped at 100) is the DRF default; every growing list
   returns the `count`/`next`/`previous`/`results` envelope with a unique ordering tiebreaker; invoice and
   payment `paid_amount`/`outstanding_balance` are annotated (one GROUP BY / one correlated subquery)
   instead of two service queries per row. Deliberately unpaginated: accounts (picker + tree), ledger
   (running balance), reports. 12 list pages read the envelope and page state; product search is
   server-side. `services/api.js` untouched. Report: `docs/audits/AUD-029-implementation-report.md`.

Committed since 012-H2: 013 auto-customer-code, 014-auto-journal-entry-code, 015 auto-vendor-code,
016 auto-invoice-number, the Frontend Design System v1, AUD-025 bcrypt, AUD-026 Celery infrastructure,
AUD-015 email delivery, and AUD-029 list pagination.
Features 001–012 (incl. H2 identity/session hardening) remain implemented. Working tree is clean.

## Verification (run this session)

- Backend: `cd backend; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` →
  **518 passed, 2 skipped** (506 baseline + 12 pagination tests; skips = 1 pre-existing + 1 opt-in
  Redis integration round-trip)
- Frontend: `npm run build` clean — 157 modules, 443.78 kB JS / 123.61 kB gzip, 11.67 kB CSS
- Frontend: `npm run lint` → **13 problems** (12 errors, 1 warning), all pre-existing categories
  (11× `react-hooks/set-state-in-effect`, 1× `exhaustive-deps`, 1× `no-undef` `process` in
  `vite.config.js`). Unchanged from the locked baseline; zero new lint debt, no rules weakened.
- Migrations: `py manage.py makemigrations --check --dry-run` → "No changes detected"
- Latest independent re-audit: `docs/audits/AUD-003-final-production-readiness-reaudit.md` →
  **GO (92/100)**, all P1 closed, no go-live blockers.

## Constraints

- **Do not push or deploy.** Committing stays with the user (no auto-commit hook is installed).
- Auth/session code is security-sensitive: do not touch `services/api.js` behavior.
- Design-system work is frontend-only; no endpoint, payload, response contract, tenant isolation,
  permission, or backend change is permitted.

## Next candidates (documented, not started)

- P2 audit items AUD-010, 011, 012 and P3 items AUD-019, 023, 027 (AUD-015 and AUD-029 are now
  closed). See `docs/audits/production-hardening-h2-report-001.md` and the AUD-003 final re-audit
  (`docs/audits/AUD-003-final-production-readiness-reaudit.md`).
- Manual visual QA of the design system was completed (`frontend-design-system-v1-visual-qa.md`); an optional
  in-browser human spot-check across both themes remains the only non-automated confirmation.
- Cleanup of the 11 pre-existing `set-state-in-effect` fetch effects.

## Quick Reference

- Docker Compose: `docker compose -f infra/docker-compose.yml up`
- H2 artifacts (prior phase): `specs/012-hardening-h2/*`, `docs/audits/production-hardening-h2-report-001.md`
<!-- SPECKIT END -->