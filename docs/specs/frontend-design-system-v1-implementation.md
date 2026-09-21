# Cetrak Frontend Design System v1 — Implementation

**Status:** Complete (Phases 0–8). Frontend-only; no backend, API, auth, payload, or database change.
**Spec:** `frontend-design-system-v1.md` | **Audit (baseline):** `frontend-design-system-v1-audit.md`

## Summary

The Cetrak frontend had no design system: styling was ~190 hard-coded hex values scattered as inline
styles across ~50 files, only 4 shared primitives existed, the global CSS was still the Vite starter
template (pinning the app to a 1126px centered column), several pages were unstyled browser defaults,
and status was communicated by color alone. This work consolidates all of it onto a tokenized,
dark-mode-aware design system without touching any business logic, service, or payload.

## Phase checklist (mirrors spec §11 definition of done)

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Audit + spec (`frontend-design-system-v1-audit.md`, `frontend-design-system-v1.md`) | Done |
| 1 | `styles/tokens.css`, `styles/globals.css`, `lib/tokens.js`; Vite starter CSS deleted | Done |
| 2 | `components/ui/*` primitives (full contract set) | Done |
| 3 | App shell: `AppShell`, `Sidebar`, `TopBar`, `PageContainer`; per-page sub-navs removed | Done |
| 4 | Login + Register/invitation polish via `AuthLayout` | Done |
| 5 | Chart of Accounts normalized as the golden reference | Done |
| 6 | System applied to remaining ERP pages (Alert/Toast/ConfirmDialog/Badge/Skeleton/EmptyState/PageHeader) | Done |
| 7 | Responsive + accessibility pass | Done |
| 8 | QA: build, lint, this implementation doc | Done |

### Phase 1 — Tokens

`src/styles/tokens.css` is the single source of truth (light + dark via `prefers-color-scheme`):
background/border/text scales, brand ramp with hover/active/soft/foreground, semantic
success/warning/danger/info (solid + soft), the single accounting-type map, typography scale,
spacing (4px base), radius, 3-level shadows, focus ring, z-index, sidebar/content dimensions.
`src/lib/tokens.js` mirrors it for JS consumers; `src/lib/cn.js` is the className helper.

Raw hex scan after implementation: **1 occurrence** (`Toggle.jsx` thumb) — fixed to
`color.brand.foreground` / `color.bg.surface`, so **zero raw hex colors remain in any component**.

### Phase 2 — Primitives

`src/components/ui/` (barrel `index.js`, 31 exports): Button, Input, Textarea, Select, Checkbox,
Radio, Toggle, Badge (+ `AccountingTypeBadge`), Card (+ Header/Body/Footer), Table, Modal, Drawer,
Dropdown, Tabs (+ TabPanel), Alert, ToastProvider/useToast, Skeleton (+ SkeletonTable), EmptyState,
ErrorState, PageHeader (+ PageContainer), ConfirmDialog, Pagination, FormField, FormSection.
All accept `className`/`style`; labels are associated via generated `id`/`htmlFor`; `aria-invalid` +
`aria-describedby` on errors; `.cetrak-*` CSS classes carry hover/focus/active and media queries
that inline styles cannot express.

### Phase 3 — Application shell

`AppShell` replaces `AppLayout`. Single data-driven `navConfig` (`src/lib/nav.js`) with role guards
that preserve the exact visibility rules of the removed `AccountingNav`/`SalesNav`/`PurchasesNav`/
`InventoryNav` sub-navs. `Sidebar` is grouped + collapsible to a 64px rail (≥1024px) and becomes a
`Drawer` below the `LG_BREAKPOINT` (1024px) breakpoint, closing on route change. `TopBar` holds the
mobile nav button, tenant switcher, and user menu with logout. `DashboardPage`'s duplicate logout
button is removed. A Dashboard link is now reachable from the shell (audit finding #11).

### Phase 4–6 — Screens

Login/Register use a centered `AuthLayout` with Card, label-associated inputs, password visibility
toggle, styled remember-me Checkbox, real loading state, and Alert for errors. **`services/api.js`,
payloads, CSRF handling, and tenant/redirect logic are byte-for-byte untouched** (verified by diff).
All 18 data pages use `PageHeader` + `PageContainer`; the 3 auth/tenant pages use `AuthLayout`.

Replacement tallies (all verified by search, zero remaining):
- `window.confirm()` — 12 call sites → `ConfirmDialog` (danger tone for destructive actions)
- `alert()` — 11 usages → `useToast()` (12 adopters)
- duplicated error/success banners (14× / 5×) → `Alert`
- ad-hoc skeletons (13×) → `Skeleton` / built-in `Table` loading
- `<select>` re-styled ~10× → shared `Select`
- dead duplicate code deleted: `components/accounting/{AccountRow,AccountTree,AccountSelect,
  JournalLineRow}.jsx` (zero importers) and `components/shared/*` (replaced in place by `ui/`)

### Phase 7 — Responsive & accessibility

Responsive via `useMediaQuery` (`useSyncExternalStore` — concurrent-safe, lint-clean) + CSS media
queries: rail at lg, drawer nav below lg, single content width (`--content-width: 1200px`) replacing
the 720/960/1024px inconsistency, horizontal table scroll in `.cetrak-table-scroll`, reduced-motion
support. Accessibility: associated labels on every input, visible focus ring on all interactive
elements, `role="dialog"` + `aria-modal` + focus trap + focus restore + Escape on Modal/Drawer,
`role="switch"` + `aria-checked` on Toggle, `aria-current` on active nav, status always text+color
(Badge), `aria-label` on icon-only buttons.

## Verification

| Gate | Baseline (audit §12) | Final |
|---|---|---|
| Build | PASS — 131 modules, 405.21 kB JS / 111.50 kB gzip, 1.78 kB CSS | PASS — 156 modules, 437.27 kB JS / 122.32 kB gzip, 11.67 kB CSS (3.32 kB gzip) |
| Lint | 18 problems (17 errors, 1 warning) | 13 problems (12 errors, 1 warning) — **zero new** |
| Tests | No frontend test suite exists (unchanged, out of scope) | — |

Lint detail — the 5 removed were exactly the unused-variable errors the audit predicted
(`Outlet` in `App.jsx`, `accessToken` in `TenantSwitcher`, and `data`/`err`/`navigate` elsewhere);
no rule was weakened or hidden. The 13 remaining are all pre-existing: 11×
`react-hooks/set-state-in-effect`, 1× `react-hooks/exhaustive-deps`, 1× `no-undef` (`process` in
`vite.config.js`).

Backend untouched and re-verified green: `421 passed, 1 skipped`
(`DJANGO_SETTINGS_MODULE=config.settings.test`), `makemigrations --check` clean.

## Constraints honored

- No Tailwind introduced (audit A-1) — built on the existing CSS-custom-property architecture.
- No manual theme toggle added (A-5) — `prefers-color-scheme` auto dark mode preserved.
- No AI nav links added (A-3) — `navConfig` is the extensibility seam for a future `AI` group.
- No forgot/reset password screens (A-4) — only Login/Register exist.
- No route paths, guards, endpoints, payloads, or auth behavior changed; no push or deploy.

## Follow-ups (not in scope for v1)

- Manual visual QA pass across both themes at each breakpoint (build/lint are automated; visual
  review is the remaining human gate).
- `react-hooks/set-state-in-effect` cleanup in the 11 data-fetch effects (pre-existing, predates
  this work) — a natural next maintenance task.
- `Pagination` is available but deliberately unwired except where a page already paginates.
