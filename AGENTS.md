<!-- SPECKIT START -->
Current phase: TWO UNCOMMITTED STREAMS IN THE WORKING TREE, BOTH COMPLETE AND VERIFIED.

1. **`specs/014-auto-journal-entry-code`** — auto-assigned journal entry references. Backend mints
   `JE-YYYY-NNNN` per tenant per year at save (`JournalEntryService.next_reference()`, collision-skip,
   max-suffix); serializer accepts blank/missing reference; new read-only preview endpoint
   `GET /accounting/journal-entries/next-reference/`; the create form shows a disabled preview and omits
   the reference from the payload. Entries stay immutable (405 on PUT/PATCH/DELETE). Report:
   `specs/014-auto-journal-entry-code/report.md` (all tasks checked in `tasks.md`).
   Note: `specs/014-auto-journal-entry/` and `specs/014-auto-customer-code/` are **superseded** drafts —
   the authoritative journal spec is `014-auto-journal-entry-code`.
2. **Frontend design system v1** — `docs/specs/frontend-design-system-v1.md` (+ audit + implementation
   doc). Tokenized, dark-mode-aware system: `styles/tokens.css` + `globals.css` + `lib/tokens.js`;
   31 exports from `components/ui/`; `AppShell`/`Sidebar`/`TopBar` replacing `AppLayout` + the four
   sub-navs; dead duplicate components deleted; 12 `window.confirm` → `ConfirmDialog`, 11 `alert()` →
   Toast. **Zero backend / API / payload / auth-behavior change** (`services/api.js` untouched).

Committed since 012-H2: 013 auto-customer-code, 015 auto-vendor-code, 016 auto-invoice-number.
Features 001–012 (incl. H2 identity/session hardening) remain implemented.

## Verification (run this session)

- Backend: `cd backend; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` →
  **421 passed, 1 skipped** (324 H2 baseline + auto-code features + 18 journal-reference tests)
- Frontend: `npm run build` clean — 156 modules, 437.27 kB JS / 122.32 kB gzip, 11.67 kB CSS
- Frontend: `npm run lint` → **13 problems** (12 errors, 1 warning), all pre-existing categories
  (11× `react-hooks/set-state-in-effect`, 1× `exhaustive-deps`, 1× `no-undef` `process` in
  `vite.config.js`). Down from the 18-problem baseline; the 5 removed were the unused-variable errors
  the audit predicted. Zero new lint debt, no rules weakened.
- Migrations: `py manage.py makemigrations --check --dry-run` → "No changes detected"

## Constraints

- **Do not push or deploy.** Committing stays with the user (no auto-commit hook is installed).
- Auth/session code is security-sensitive: do not touch `services/api.js` behavior.
- Design-system work is frontend-only; no endpoint, payload, response contract, tenant isolation,
  permission, or backend change is permitted.

## Next candidates (documented, not started)

- P2 audit items AUD-010, 011, 012, 015, 025, 026 and P3 items AUD-019, 023, 027, 029 — natural next:
  AUD-025 (bcrypt), AUD-026 (Celery). See `docs/audits/production-hardening-h2-report-001.md`.
- Manual visual QA of the design system across both themes at each breakpoint (the one remaining
  human gate; build/lint are automated).
- Cleanup of the 11 pre-existing `set-state-in-effect` fetch effects.

## Quick Reference

- Docker Compose: `docker compose -f infra/docker-compose.yml up`
- H2 artifacts (prior phase): `specs/012-hardening-h2/*`, `docs/audits/production-hardening-h2-report-001.md`
<!-- SPECKIT END -->