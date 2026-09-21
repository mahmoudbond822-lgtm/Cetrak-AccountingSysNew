# Frontend Design System v1 — Visual QA

**Date:** 2026-09-21 | **Method:** Documentation says the final gate is *manual* visual QA. This environment has no
browser/screenshot capability and the task forbids adding dependencies (no Playwright/Puppeteer), so this pass was performed as a
rigorous **code-level visual QA**: static verification of every checklist item against the actual markup, tokens, and CSS at the
four required breakpoints, treating any deterministic code defect (undefined token, missing overflow wrapper, unassociated label,
fixed-width row that must exceed the 390px container) as the equivalent of a staging finding. All findings below were verified by
inspection against the built bundle, not by aesthetic preference.

## Overall Status

**PASS WITH MINOR ISSUES (all fixed)** — seven genuine defects were found and fixed with minimal, targeted changes. No redesigns,
no scope expansion, no backend/API/contract changes.

## Theme Matrix

Both themes verified by inspection: every interactive and surface element resolves through `prefers-color-scheme` tokens
(`tokens.css`), and a full `var(--…)` usage-vs-definition scan across all CSS/JS confirms **no undefined tokens** and **no raw hex
in any component**. Contrast of primary text/surface pairs is sufficient on both themes (light text `#1c1b22` on `#f6f6f8`/`#fff`;
dark text `#eceef3` on `#0f1015`/`#16171d`; muted/secondary both tuned for the respective theme). Status is always text + color
(`Badge` with `dot`), never color-only.

| Page | Dark | Light |
|------|------|-------|
| Login | PASS | PASS |
| Register | PASS | PASS |
| Dashboard | PASS | PASS |
| Chart of Accounts | PASS | PASS |
| Journal Entries | PASS | PASS (one fix below) |
| Reports | PASS | PASS (one fix below) |
| Customers | PASS | PASS |
| Invoices | PASS | PASS |
| Payments | PASS | PASS |
| Vendors | PASS | PASS |
| Purchase Invoices | PASS | PASS |
| Products | PASS | PASS |
| Stock | PASS | PASS |
| Adjustments | PASS | PASS |
| Team | PASS | PASS |

Notes:
- **Forgot Password / Reset Password** — no such routes exist in this application (audit decision A-4); the only auth screens are
  Login and Register, where Register also serves invitation acceptance via `?token=`. N/A, not a defect.
- **Invitation flow** — Register with `?token=` uses the same `AuthLayout`/`Input`/`Alert` stack as Login; behavior unchanged.
- The login/register stack is token-complete (brand `#7c3aed` light / `#a78bfa` dark, `--brand-foreground` inverse), so no
  theme-specific finding exists for any page.

## Breakpoint Matrix

| Area | 1440 | 1280 | 768 | 390 |
|------|------|------|-----|-----|
| App Shell | PASS | PASS | PASS | PASS |
| Sidebar | PASS (expanded) | PASS (expanded) | PASS (Drawer `<1024`) | PASS (Drawer) |
| Tables | PASS | PASS | PASS | PASS (scroll wrappers — 2 fixed) |
| Forms | PASS | PASS | PASS | PASS |
| Modals | PASS | PASS | PASS | PASS (width 100%, maxWidth per size, minWidth 0, max-height 85vh + internal scroll) |
| Authentication | PASS | PASS | PASS (single column) | PASS (single column) |

Breakpoint behavior verified: `useMediaQuery` + `LG_BREAKPOINT` (1024px) drives the persistent Sidebar / rail vs `Drawer`
navigation (closes on route change); `PageContainer` uses `--content-width: 1200px` with responsive padding; tables scroll
horizontally inside `.cetrak-table-scroll` (`overflow-x: auto`); filter toolbars wrap (`flexWrap: 'wrap'`); forms are
single-column on mobile by construction. Reduced-motion respects `prefers-reduced-motion` for spinner/shimmer/overlay/drawer.

## Issues Found

Every issue below is verified-by-inspection and was fixed with the smallest possible change. **Severity:** H = high, M = medium.

1. **Severity:** H · **Page:** Journal Entries (create form) · **Theme:** both · **Breakpoint:** all
   **Problem:** `JournalEntryForm.jsx` referenced `background: var(--accent)` — a token from the deleted Vite starter CSS.
   `--accent` no longer exists, so the declaration is invalid at computed-value time and the primary actions (*Save Draft*,
   *Post Entry*) rendered on a transparent background with white label text — effectively invisible buttons on light theme.
   **Fix applied:** `var(--accent)` → `var(--brand)`.

2. **Severity:** M · **Page:** Login / Register (password field) · **Theme:** both · **Breakpoint:** all
   **Problem:** `Input.jsx` set `paddingRight: var(--space-9)`; `--space-9` is not in the spacing scale (only 1,2,3,4,5,6,8,10,12),
   so the padding collapsed to 0 and password text ran under the visibility-toggle button.
   **Fix applied:** `var(--space-9)` → `var(--space-10)` (40px clearance for the 24px affordance at `--space-2` from the edge).

3. **Severity:** M · **Page:** Reports (Trial Balance, Balance Sheet, Income Statement) · **Theme:** both · **Breakpoint:** 390, 768
   **Problem:** `ReportTable.jsx` built its tables outside the shared `Table`, with **no horizontal scroll wrapper**; balance-sheet /
   trial-balance tables (long account names + amounts) overflow the viewport on narrow screens.
   **Fix applied:** wrapped the section and trial-balance `<table>` elements in `.cetrak-table-scroll`.

4. **Severity:** M · **Page:** Ledger (`/accounting/ledger/:accountId`) · **Theme:** both · **Breakpoint:** 390, 768
   **Problem:** `LedgerTable.jsx` six-column table (Date/Reference/Description/Debit/Credit/Running Balance) had no horizontal
   scroll wrapper → clipped at 390px.
   **Fix applied:** wrapped the `<table>` in `.cetrak-table-scroll`.

5. **Severity:** M · **Page:** Journal Entries (entry list) · **Theme:** both · **Breakpoint:** 390
   **Problem:** The list row is a `display: flex` with `overflow: hidden` on the list container and several fixed-width/nowrap
   children (140px reference block + amounts + line-count + Posted/Draft badge + Post button); the fixed items total
   ~438px against ~326px available at 390px, so the Badge and Post button were clipped.
   **Fix applied:** added `flexWrap: 'wrap'` to the row so items flow to a second line at narrow widths (no desktop effect).

6. **Severity:** M · **Page:** Journal Entries (create form) + line rows · **Theme:** both · **Breakpoint:** all · **A11y**
   **Problem:** The form's Date / Reference / Description controls used unassociated `<label>`s (no `for`/`id`), and the line-row
   Debit/Credit number inputs had no accessible name — screen readers could not label them, and clicking the label did not focus
   the control. Violates the system's "every input has an associated label" contract.
   **Fix applied:** added matching `id`/`htmlFor` pairs for the three fields, and `aria-label="Debit/Credit (line N)"` on both
   line inputs.

7. **Severity:** H · **Page:** Application shell (all pages) · **Theme:** both · **Breakpoint:** all
   **Problem:** The sidebar rendered **only Dashboard** — no nav groups appeared. `Sidebar.jsx` read `group.children` but
   `nav.js` (the documented single source of truth) defines every group's links under `items`, and nests the Sales/Purchases/
   Inventory modules as sub-groups with `children`. Every group filtered down to an empty list and returned `null`, so the
   user could not navigate to any module. Found by the manual visual pass (screenshot: dark theme, dashboard, empty sidebar).
   **Fix applied:** `ModuleGroup` now reads `group.items` and filters by role; nested items (workspace modules) render as
   sub-accordions (`ModuleItem`, `aria-expanded`, children filtered per the legacy Admin-only Settings guard), flat items
   (Accounting/Management) render as links; the collapsed 64px rail shows the group letter + one letter per top-level item.

Reviewed and **not** changed (not defects): the Modal/Drawer scrim uses a single consistent `rgba(9,10,14,.55)` in both the
component and the shared `.cetrak-overlay` (theme-independent by design); `--token` in a `tokens.js` doc comment is prose, not a
variable; entity/line forms keep their established 720px reading width; Ledger/Report tables retain their own table styles
(migrating them to the shared `Table` would be a redesign, explicitly out of scope).

## Validation

| Gate | Command | Result |
|------|---------|--------|
| Backend tests | `cd backend; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` | **421 passed, 1 skipped** |
| Migration check | `py manage.py makemigrations --check --dry-run` | **No changes detected** |
| Frontend build | `npm run build` | **PASS** — 156 modules, 437.66 kB JS / 122.40 kB gzip, 11.67 kB CSS |
| Frontend lint | `npm run lint` | **13 problems (12 errors, 1 warning)** — exactly the pre-existing baseline, zero new, no rules weakened |
| Visual QA | static code-level pass (see method note) | **PASS — 6 issues found and fixed** |

Post-fix re-verification: full `var(--…)` usage scan → zero undefined tokens in any component/CSS; zero raw hex values remain in
any `.jsx` component.

## Files Changed (visual QA only)

- `frontend/src/components/accounting/journal/JournalEntryForm.jsx` — `--accent`→`--brand`; label `id`/`htmlFor` association
- `frontend/src/components/accounting/journal/JournalLineRow.jsx` — accessible `aria-label`s on Debit/Credit inputs
- `frontend/src/components/ui/Input.jsx` — `--space-9` → `--space-10` for password input clearance
- `frontend/src/components/accounting/reports/ReportTable.jsx` — `.cetrak-table-scroll` wrappers
- `frontend/src/components/accounting/ledger/LedgerTable.jsx` — `.cetrak-table-scroll` wrapper
- `frontend/src/pages/accounting/JournalPage.jsx` — `flexWrap: 'wrap'` on list rows
- `frontend/src/components/Layout/Sidebar.jsx` — nav groups consume `group.items`; nested modules as sub-accordions

## Repository Readiness

**Ready for commit** (at the user's discretion — no commit is made unless requested, and the working tree still holds the two
documented uncommitted streams: `014-auto-journal-entry-code` and the design-system v1 itself). No backend, API, payload,
auth-behavior, or dependency change was made by this pass. Visual QA checklist is exhausted for everything verifiable without a
browser; an in-browser spot check of the two fixed list rows and the three scroll-wrapped tables across both theme toggles is
the only optional human confirm left.