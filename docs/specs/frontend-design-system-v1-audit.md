# Cetrak Frontend Design System v1 — Repository Audit

**Date:** 2026-09-20
**Scope:** `frontend/` (React 19 + Vite). No backend changes.
**Purpose:** Establish the factual baseline for the Cetrak design system before any code changes.

---

## 1. Executive summary

The Cetrak frontend is **functionally complete but visually unconsolidated**. It works, but it has **no design system**: styling is scattered as inline `style` objects across ~50 files, there are only **4 shared components**, the global CSS is still the **Vite starter template** (which actively harms layout), and several pages are **100% unstyled browser-default HTML**.

The single most important finding: **Tailwind CSS is not installed anywhere in this repository**, even though the project brief lists "Tailwind CSS v4" as the stack. The entire UI is built from inline styles + a small set of CSS custom properties. Any design system must therefore be built on the **existing CSS-custom-property architecture** (see §9, Decision A-1).

---

## 2. Current architecture

```
frontend/
├── index.html                     # title = "frontend" (not branded)
├── vite.config.js                 # react plugin + /api proxy
├── eslint.config.js               # eslint flat config (js recommended + react-hooks + react-refresh)
├── package.json                   # NO tailwindcss, NO test runner
└── src/
    ├── main.jsx                   # imports index.css
    ├── App.jsx                    # all routes (see §3)
    ├── index.css                  # ⚠ VITE STARTER TEMPLATE (see §5.1)
    ├── App.css                    # ⚠ VITE STARTER TEMPLATE (unused by app)
    ├── pages/                     # 22 pages
    ├── components/
    │   ├── Layout/                # AppLayout, ProtectedRoute, TenantSwitcher, 4× *Nav
    │   ├── shared/                # Button, Input, Modal, Table  ← the ONLY shared UI
    │   └── {accounting,sales,purchases,inventory}/  # feature components
    ├── services/                  # api.js + 4 feature services (axios)
    └── hooks/useAccounting.js
```

**Stack actually in use:** React 19.2, Vite 8, react-router-dom 7, axios. JavaScript only (no TypeScript). Node v24.

---

## 3. Routes (complete inventory)

| Path | Page | Notes |
|---|---|---|
| `/login` | LoginPage | unstyled browser HTML |
| `/register` | RegisterPage | unstyled; doubles as invitation acceptance via `?token=` |
| `/tenant-select` | TenantSelectPage | protected, outside AppLayout |
| `/` | DashboardPage | unstyled browser HTML |
| `/team` | TeamPage | unstyled browser HTML (`<table border="1">`) |
| `/accounting/accounts` | AccountsPage | uses shared Modal/Button/Input |
| `/accounting/journal` | JournalPage | custom row list |
| `/accounting/ledger/:accountId` | LedgerPage | |
| `/accounting/reports` | ReportsPage | hidden from Manager role |
| `/sales/{customers,invoices,payments,settings}` | | |
| `/purchases/{vendors,invoices,payments,settings}` | | |
| `/inventory/{products,stock,adjustments,settings}` | | |

**No forgot-password / reset-password routes exist.** No AI routes exist. No 404 route.

All app routes are wrapped in `AppLayout` (sidebar + `<Outlet />`) and `ProtectedRoute`.

---

## 4. Existing reusable components (complete inventory)

Only **4** shared UI components exist in `components/shared/`:

| Component | API | Gaps |
|---|---|---|
| `Button` | `variant ∈ {primary, secondary, danger}`, `disabled` | no ghost/outline/link, no `loading`, no sizes, no hover/active states (inline styles can't express `:hover`), hard-coded `#F44336` |
| `Input` | `label`, `error` | no `helperText`, no `disabled` style, no `required` marker, label not associated (`htmlFor`/`id`), no password-visibility, no textarea/select/number/search, hard-coded `#F44336` |
| `Modal` | `open`, `onClose`, `title`, `children`, `footer` | Escape works, but **no `role="dialog"`, no focus trap, no `aria-modal`, no restore focus, card hard-coded `background:#fff`** (breaks dark mode) |
| `Table` | `columns`, `data`, `footer`, `emptyMessage`, `col.align` | no loading state, no hover, no sticky header, no responsive overflow wrapper, header hard-coded `#f9f9f9` (breaks dark mode), `key={row.id ?? i}` |

**Missing primitives (currently re-implemented ad-hoc per page or absent):**
Select, Checkbox, Radio, Toggle, Badge, Card, Drawer, Dropdown/Menu, Tabs, Toast, Alert, Skeleton, EmptyState, ErrorState, PageHeader, FormSection, ConfirmDialog, Pagination.

---

## 5. Existing styling approach & theme tokens

### 5.1 `index.css` is the Vite starter template — a live defect

```css
#root { width: 1126px; max-width: 100%; margin: 0 auto; text-align: center; border-inline: 1px solid var(--border); }
h1 { font-size: 56px; letter-spacing: -1.68px; margin: 32px 0; }
h2 { font-size: 24px; ... }
```

This pins the whole app to a **1126px centered column with centered text and a hairline border around the viewport**. It is the main reason the product "looks like an internal tool". `App.css` (hero/counter styles) is dead weight from the same template. Every page then fights it with inline styles, and page titles override the 56px `h1` with `fontSize: '1.5rem'`.

### 5.2 Token inventory (all of them)

`index.css :root` defines exactly these, with a dark override under `@media (prefers-color-scheme: dark)`:

```
--text, --text-h, --bg, --border, --code-bg, --accent, --accent-bg,
--accent-border, --social-bg, --shadow, --sans, --heading, --mono
```

That is the entire "theme". There is **no surface/elevated scale, no semantic colors, no typography scale, no spacing/radius/shadow scale, no focus token**. Dark mode exists only via OS preference (no toggle).

### 5.3 Inline-style convention

Every component uses React inline `style` objects. Consequence: **no `:hover`, `:focus`, `:active`, or media queries are possible** — so interactive elements have no hover/feedback and the app has **zero responsive behavior**. Any design system must supply a small CSS layer for pseudo-classes, focus rings, and responsive utilities (see §9, Decision A-2).

### 5.4 Hard-coded color audit

- **~190 hard-coded hex colors** across `src/**/*.jsx`.
- The same error banner inline object is copy-pasted **14 times**:
  `background: '#FFF3F3', border: '1px solid #F44336', color: '#F44336'`
- The same success/notice banner is copy-pasted **~5 times** (`#F0F8F0 / #4CAF50 / #2E7D32`).
- `background: '#f9f9f9'` table headers **6 times**; `background: '#fff'` surfaces ~8 times.
- `color: 'red'` plain-text errors in Login/Register/Team.
- **Every one of these is a light-only color that breaks the app's own dark mode.** This is a real, user-visible defect, not just cosmetics.

### 5.5 Accounting semantic colors are not centralized

`AccountRow.jsx` owns a local `typeColors` map (`Asset #4CAF50, Liability #F44336, Equity #2196F3, Revenue #FF9800, Expense #9C27B0`) — plus it uses a **bare color dot with no text label**, which violates the "don't rely on color alone" accessibility rule. Status colors (Posted/Draft badges) are similarly re-defined inline in `JournalPage`.

---

## 6. Problems found (by category)

### 6.1 Design language
1. No design tokens beyond ~13 CSS variables; brand purple (`--accent`) is used as both button fill and focus outline with no hover/active ramp.
2. No typography hierarchy — global `h1` is 56px starter styling; pages locally use `1.5rem`; section titles, card titles, captions undefined.
3. Inconsistent page max-widths: `720px` (settings), `960px` (most), `1024px` (stock) — same product, three widths.
4. Inconsistent border radii (`4px`, `6px`, `8px`, `10px`, `12px`) with no scale.
5. Buttons styled at least 3 different ways: `shared/Button`, local `btnPrimary` objects (8 pages), and plain unstyled `<button>` (Login/Register/Dashboard/Team).
6. Status communicated by color-only dots/spans; no Badge component.

### 6.2 Components & duplication
7. Error/loading/empty/skeleton markup re-implemented on **every** page (13× `pageStyle`/`titleStyle`/`skeletonStyle`).
8. `<select>` elements re-styled inline ~10 times with slightly different padding/colors and **no shared Select component**.
9. Native `window.confirm()` used for **12 destructive/state-changing actions**; native `alert()` for **~11 error toasts**. These are unstyled, blocking, and inconsistent with a premium product.
10. **Dead duplicate code:** `components/accounting/{AccountRow, AccountTree, AccountSelect, JournalLineRow}.jsx` have **zero importers** (the canonical copies live in `accounts/` and `journal/` subfolders). `AccountTree` copy is byte-identical.

### 6.3 Application shell
11. **No Dashboard link in the sidebar** — the root route is unreachable from the shell; `DashboardPage` ships its own duplicate logout button + `TenantSwitcher` instead.
12. Logout logic duplicated in `AppLayout` and `DashboardPage`.
13. Sidebar is a flat 220px column with no collapse, no mobile drawer, no sections other than plain uppercase labels; it will not scale as modules grow.
14. **Double navigation:** every page renders a horizontal sub-nav (`AccountingNav`, `SalesNav`, `PurchasesNav`, `InventoryNav`) *in addition to* the sidebar — redundant and cluttered.
15. No TopBar: no global tenant switcher placement, no user menu, no session identity outside the sidebar.
16. `TenantSwitcher` dropdown is hand-rolled with hard-coded `#fff/#ccc/#eee` (breaks dark mode), no outside-click close, no keyboard support, no Escape.

### 6.4 Accessibility
17. `<label>` elements are **never** associated with inputs (no `htmlFor`/`id`) — screen readers can't bind them.
18. Modal lacks `role="dialog"`, `aria-modal`, focus trap, and focus restore.
19. No visible focus styles anywhere except the starter `:focus-visible` on `.counter` (dead CSS).
20. Login/Register forms: unstyled native controls, no `aria-invalid`, no error association.
21. Accounting type indicated by a color dot only (WCAG 1.4.1).

### 6.5 Responsive
22. **Zero responsive behavior.** Fixed `#root { width: 1126px }`, fixed `220px` sidebar, no breakpoints, no mobile drawer; tables will overflow small screens; forms never collapse to one column.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Big-bang rewrite breaks working ERP logic | Refactor in place; keep all business logic, services, and payloads untouched |
| Auth flow is security-sensitive (JWT cookie + CSRF) | **Do not touch** `services/api.js` behavior; only swap markup/labels in auth pages |
| Dark mode already half-exists | Make every new token dark-mode-aware from day 1; delete hard-coded light colors |
| Removing sub-navs changes navigation muscle memory | Sidebar will expose the same destinations; document in implementation report |
| No test suite exists to catch regressions | Lean on `npm run build` + `npm run lint` + manual visual QA; do not add a test runner out of scope |
| Uncommitted work from feature branch `014-auto-customer-code` exists in `backend/` and 3 frontend files | **Do not touch** those files; changes are design-system only |

---

## 8. Proposed component architecture

Adapt the requested structure to the existing repo (no duplicate directories — `components/shared/` is consolidated into `components/ui/`):

```
src/
├── styles/
│   ├── tokens.css        # ALL design tokens (light + dark) as CSS variables
│   ├── globals.css       # reset, base typography, focus ring, scrollbar, utilities
├── lib/
│   ├── tokens.js         # JS mirror of tokens for inline-style consumers
│   └── cn.js             # tiny className helper
├── components/
│   ├── ui/               # Button, Input, Select, Checkbox, Radio, Toggle, Badge,
│   │                     # Card, Table, Modal, Drawer, Dropdown, Tabs, Toast,
│   │                     # Alert, Skeleton, EmptyState, ErrorState, PageHeader,
│   │                     # ConfirmDialog, Pagination, FormField
│   ├── layout/           # AppShell, Sidebar, TopBar, PageContainer  (lowercase `layout/`)
│   └── (existing feature components stay in place)
```

`components/shared/` is replaced by `components/ui/`; the 4 existing components are refactored *in place* (moved + upgraded) so every existing importer is updated rather than duplicated.

**Rule applied:** *if a pattern appears more than once or is clearly foundational, make it reusable.* The error banner (14×), page header (13×), skeleton (13×), select (10×), confirm dialog (12×), toast (11×) all clear that bar.

---

## 9. Proposed design tokens (summary)

Full scale defined in the spec (`frontend-design-system-v1.md`):

- **Color:** background (`app`/`surface`/`elevated`/`hover`/`active`), border (`default`/`subtle`/`strong`), text (`primary`/`secondary`/`muted`/`disabled`/`inverse`), brand (`primary` + `hover`/`active`/`soft`/`foreground`), semantic (`success`/`warning`/`danger`/`info`, each + `soft`), all with dark counterparts.
- **Accounting semantics:** `asset`, `liability`, `equity`, `revenue`, `expense` (+ soft) — one map, used everywhere, never re-defined per page.
- **Typography:** display / pageTitle / sectionTitle / cardTitle / body / bodySmall / caption / label / tableHeader / tableBody — weights and line-heights intentional.
- **Spacing:** `4/8/12/16/20/24/32/40/48` (4px base). **Radius:** `sm 6` / `md 8` / `lg 12` / `pill 999`. **Shadow:** 3 subtle levels. **Focus:** one `--focus-ring` token.
- **Dark mode:** default `light`, auto dark via `prefers-color-scheme` (preserves current behavior); every token defined for both.

---

## 10. Key audit decisions (locked)

- **A-1 — Do not introduce Tailwind.** The brief states the stack is Tailwind v4, but the repo has no Tailwind dependency, config, or a single utility class. Installing it now would mean rewriting ~50 files of inline styles — a "rewrite from scratch", explicitly forbidden. **The design system is built on the existing CSS-custom-property architecture** (`styles/tokens.css` + `lib/tokens.js`), which satisfies "centralized design tokens exist" with far lower risk. Documented per Spec-Kit discipline §22 (existing project convention wins unless it creates a real design-system problem; inline styles do not).
- **A-2 — Add a minimal CSS layer.** Inline styles cannot express `:hover/:focus/:active` or media queries, which the design system requires. A small `globals.css` with utility classes (`cetrak-button`, `cetrak-input`, focus ring, table hover, responsive helpers) closes this gap without a framework.
- **A-3 — No AI navigation links.** No AI routes exist. The nav becomes a data-driven, extensible config so an `AI` group can be added later without shell changes, but **no fake/broken links are added now**.
- **A-4 — No forgot/reset password screens.** Those routes do not exist; only Login and Register (incl. invitation acceptance) are redesigned.
- **A-5 — Keep `prefers-color-scheme` auto dark mode** (no manual toggle) to preserve current behavior; dark stays primary per brief.

---

## 11. Proposed implementation order

| Phase | Deliverable | Risk |
|---|---|---|
| 0 | This audit + `frontend-design-system-v1.md` | none |
| 1 | `styles/tokens.css`, `styles/globals.css`, `lib/tokens.js`; delete Vite starter CSS | low |
| 2 | `components/ui/*` primitives (Button, Input, Select, Checkbox, Radio, Toggle, Badge, Card, Table, Modal, Drawer, Dropdown, Tabs, Toast, Alert, Skeleton, EmptyState, ErrorState, PageHeader, ConfirmDialog, Pagination, FormField) | low — additive |
| 3 | App shell: `AppShell`, `Sidebar` (grouped, collapsible, mobile drawer), `TopBar` (tenant + user menu), `PageContainer`; remove redundant per-page sub-navs | medium — nav change |
| 4 | Login + Register/invitation polish | low |
| 5 | Chart of Accounts — golden reference | low |
| 6 | Apply system to remaining ERP pages (Alert/Toast/ConfirmDialog/Badge/Skeleton/EmptyState/PageHeader) | medium — broad |
| 7 | Responsive + accessibility pass | low |
| 8 | QA: `npm run build`, `npm run lint`, visual review, implementation doc + report | none |

---

## 12. Baseline quality gates (recorded before changes)

| Gate | Command | Baseline result |
|---|---|---|
| Build | `npm run build` | **PASS** — 131 modules, `index-*.js 405.21 kB` (gzip 111.50 kB), `index-*.css 1.78 kB` |
| Lint | `npm run lint` | **18 pre-existing problems** (17 errors, 1 warning): 10× `react-hooks/set-state-in-effect`, `no-undef` `process` in `vite.config.js`, `no-unused-vars` (`Outlet`, `accessToken`, `data`, `err`×2, `navigate`), 1× `react-hooks/exhaustive-deps` |
| Tests | — | **No frontend test suite exists** (no vitest/jest dependency, no test files) |

The lint count is **pre-existing** and will not be hidden or rule-weakened. Where a refactor naturally removes a pre-existing lint error (e.g. the unused `Outlet` import in `App.jsx`, unused `accessToken` in `TenantSwitcher`), that is a bonus and will be listed in the implementation report.
