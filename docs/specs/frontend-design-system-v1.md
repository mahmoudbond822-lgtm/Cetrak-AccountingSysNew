# Cetrak Frontend Design System v1 — Specification

**Status:** Authoritative for the frontend design system + UX foundation work.
**Scope:** Frontend only. No backend, API, auth-behavior, or database changes.
**Parent audit:** `docs/specs/frontend-design-system-v1-audit.md`

---

## 1. Product design direction

Cetrak must read as **professional financial software with modern AI capabilities**:
clean, calm, premium, data-focused, trustworthy. Not flashy, not "neon AI startup",
not legacy accounting. Dark theme is primary; light theme supported via OS preference.
Purple remains the brand accent — as a **controlled token**, never a hard-coded literal.

**Anti-goals:** excessive gradients, oversized rounding, oversized type, unnecessary
animation, visual clutter, page-to-page inconsistency.

---

## 2. Design tokens

Single source of truth: `src/styles/tokens.css` (CSS custom properties, light + dark).
JS consumers import from `src/lib/tokens.js` (a mirror that keeps inline-style components
on-token). **No raw hex color may appear in a component.**

### 2.1 Color — background / border / text

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg-app` | `#f6f6f8` | `#0f1015` | app background |
| `--bg-surface` | `#ffffff` | `#16171d` | cards, sidebar, topbar |
| `--bg-elevated` | `#ffffff` | `#1d1f27` | modals, dropdowns, popovers |
| `--bg-hover` | `#f1f1f4` | `#22242e` | row/item hover |
| `--bg-active` | `#e9e9ee` | `#2a2d39` | pressed / selected |
| `--border` | `#e4e4e9` | `#2b2e39` | default border |
| `--border-subtle` | `#efeff3` | `#232530` | hairline |
| `--border-strong` | `#cfced6` | `#3a3d4c` | emphasis / focus boundary |
| `--text` | `#1c1b22` | `#eceef3` | primary |
| `--text-secondary` | `#54535e` | `#a8abb8` | secondary |
| `--text-muted` | `#7a7986` | `#7d8190` | muted / captions |
| `--text-disabled` | `#a8a7b0` | `#5c5f6c` | disabled |
| `--text-inverse` | `#ffffff` | `#0f1015` | on brand fill |

### 2.2 Brand (purple)

| Token | Light | Dark |
|---|---|---|
| `--brand` | `#7c3aed` | `#a78bfa` |
| `--brand-hover` | `#6d28d9` | `#b79dfd` |
| `--brand-active` | `#5b21b6` | `#8b5cf6` |
| `--brand-soft` | `rgba(124,58,237,.10)` | `rgba(167,139,250,.16)` |
| `--brand-foreground` | `#ffffff` | `#14101f` |

Brand is used sparingly: primary buttons, active nav indicator, focus ring, key links.

### 2.3 Semantic

| Token | Light (solid / soft) | Dark (solid / soft) | Meaning |
|---|---|---|---|
| `--success` | `#15803d` / `rgba(21,128,61,.10)` | `#4ade80` / `rgba(74,222,128,.15)` | posted, active, positive |
| `--warning` | `#b45309` / `rgba(180,83,9,.10)` | `#fbbf24` / `rgba(251,191,36,.15)` | draft, pending |
| `--danger` | `#dc2626` / `rgba(220,38,38,.10)` | `#f87171` / `rgba(248,113,113,.15)` | destructive, error |
| `--info` | `#2563eb` / `rgba(37,99,235,.10)` | `#60a5fa` / `rgba(96,165,250,.15)` | informational |

Soft variants are used for Badge/Alert fills; solid for text/borders. **Status is never
communicated by color alone** — a text label always accompanies it.

### 2.4 Accounting semantic colors (single global map)

| Type | Light solid / soft | Dark solid / soft |
|---|---|---|
| Asset | `#047857` / `rgba(4,120,87,.10)` | `#34d399` / `rgba(52,211,153,.15)` |
| Liability | `#b91c1c` / `rgba(185,28,28,.10)` | `#f87171` / `rgba(248,113,113,.15)` |
| Equity | `#1d4ed8` / `rgba(29,78,216,.10)` | `#60a5fa` / `rgba(96,165,250,.15)` |
| Revenue | `#b45309` / `rgba(180,83,9,.10)` | `#fbbf24` / `rgba(251,191,36,.15)` |
| Expense | `#7c3aed` / `rgba(124,58,237,.10)` | `#a78bfa` / `rgba(167,139,250,.15)` |

Exposed as `accountingTypeTokens` in `lib/tokens.js`. Consumed by AccountRow, reports,
and any ledger UI. **Never re-defined per page.**

### 2.5 Typography

Font stack: `--font-sans: 'Inter', system-ui, 'Segoe UI', Roboto, sans-serif`;
`--font-mono: ui-monospace, 'SF Mono', Consolas, monospace` (figures in tables may use tabular
alignment via class).

| Token | Size / weight / line-height | Use |
|---|---|---|
| `--text-display` | 30 / 600 / 1.2 | auth hero, empty-state title |
| `--text-page-title` | 22 / 600 / 1.3 | `PageHeader` title |
| `--text-section-title` | 17 / 600 / 1.4 | section / card title |
| `--text-card-title` | 15 / 600 / 1.4 | card title |
| `--text-body` | 14 / 400 / 1.5 | default body |
| `--text-body-small` | 13 / 400 / 1.5 | dense table body, helpers |
| `--text-caption` | 12 / 400 / 1.45 | captions, timestamps |
| `--text-label` | 13 / 500 / 1.4 | form labels, table headers |
| `--text-table-header` | 12 / 600 / 1.4, uppercase, `letter-spacing .04em` | table header |

No element exceeds 30px. Base `font-size: 14px` on `:root`.

### 2.6 Spacing, radius, shadow, focus

- **Spacing (4px base):** `--space-1: 4`, `--space-2: 8`, `--space-3: 12`, `--space-4: 16`,
  `--space-5: 20`, `--space-6: 24`, `--space-8: 32`, `--space-10: 40`, `--space-12: 48`.
- **Radius:** `--radius-sm: 6px`, `--radius-md: 8px`, `--radius-lg: 12px`, `--radius-pill: 999px`.
  Cards/inputs/buttons use `sm`/`md`; `pill` only for badges.
- **Shadow (subtle only):** `--shadow-xs` (hairline emphasis), `--shadow-sm` (dropdowns),
  `--shadow-md` (popovers), `--shadow-lg` (modal/dialog).
- **Focus:** `--focus-ring: 0 0 0 2px var(--bg-surface), 0 0 0 4px var(--brand)` — visible on
  both themes, applied via `.cetrak-focus-visible` utility and on all interactive primitives.
- **Z-index:** `--z-dropdown: 100`, `--z-sticky: 200`, `--z-drawer: 900`, `--z-modal: 1000`,
  `--z-toast: 1100`.
- **Sidebar width:** `--sidebar-width: 248px`; collapsed `--sidebar-width-collapsed: 64px`.

---

## 3. Core component contracts

All primitives live in `src/components/ui/`. All accept `className` + `style` unless noted.
Buttons are `<button>`; links are `<a>`/`<Link>`; interactive non-navigation elements are
never `<div>`.

### Button
`variant: primary|secondary|ghost|outline|danger|link`; `size: sm|md`; `loading: boolean`;
`disabled`; `icon`. Loading shows a spinner and disables. Hover/active/disabled handled by
the `.cetrak-button` CSS class (inline styles cannot express pseudo-classes). `danger` is
visually distinct (red outline/solid) from normal actions and is never the default action.

### Input / Textarea
`type: text|email|password|number|search`; `label`, `helperText`, `error`, `required`,
`disabled`, `placeholder`, `leftIcon`, `rightSlot`. Password type gains a visibility toggle
button with `aria-label`. Label is associated via generated `id`/`htmlFor`; `aria-invalid`
+ `aria-describedby` when error/helper present. Error text uses `--danger`.

### Select
Native `<select>` styled with a chevron (not a custom listbox — avoids complexity, keeps
keyboard/a11y for free). Same label/error/helper contract as Input.

### Checkbox / Radio / Toggle
Associated label, `indeterminate` support on Checkbox; Toggle is `role="switch"` with
`aria-checked`; Radio supports a `RadioGroup` context.

### Badge
`variant: neutral|brand|success|warning|danger|info`; `size: sm|md`; optional `dot`.
`AccountingTypeBadge({ type })` renders `<Badge dot>{type}</Badge>` with the accounting map.
Status badges pair text + color (never color-only).

### Card
`Card`, `CardHeader`, `CardBody`, `CardFooter` — surface bg, `--radius-md`, `--border`,
`--shadow-xs`. No excessive rounding or shadow.

### Table
`columns: [{ key, label, align, render, width, numeric }]`, `data`, `loading`, `emptyState`,
`error`, `onRowClick`, `rowKey`, `footer`. Features: sticky header, hover rows, numeric
right-alignment via `numeric`, actions column right-aligned, **responsive horizontal scroll**
wrapper (`.cetrak-table-scroll`), built-in Skeleton loading, built-in EmptyState when
`data.length === 0`. Replaces ad-hoc per-page skeletons/empties.

### Modal
`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, focus trap, focus restore, Escape to
close, overlay click to close (configurable), body scroll lock. Drawer is the side variant
(`side: right|left`, used for the mobile nav).

### ConfirmDialog
Built on Modal: `title`, `description`, `confirmLabel`, `cancelLabel`, `tone: default|danger`,
`onConfirm`. Replaces every `window.confirm()` — including the 12 destructive ERP actions —
with a styled, consistent, accessible confirmation (danger tone for destructive).

### Alert
`tone: error|success|warning|info`; `title`, `children`, `dismissible`, `icon`. Replaces the
14 duplicated inline error banners and 5 success banners.

### Toast
`ToastProvider` + `useToast()` → `toast.success/error/info/warning(msg)`. Non-blocking,
auto-dismiss, `role="status"`/`role="alert"`, Escape dismiss, stacked top-right. Replaces the
11 `alert()` error usages.

### Skeleton / EmptyState / ErrorState
- `Skeleton` (`width`, `height`, `radius`, `count`) for loading rows.
- `EmptyState` (`icon`, `title`, `description`, `action`) — "No accounts yet", etc.
- `ErrorState` (`title`, `description`, `retryAction`) for failed loads.

### PageHeader
`title`, `description`, `breadcrumbs?`, `primaryAction?`, `secondaryActions?`. Standard page
top; every page uses it. Also `PageContainer` (max-width, responsive padding).

### Pagination
`page`, `pageSize`, `total`, `onPageChange` — present for future API pagination; adopted only
where a page already paginates (prevents premature wiring).

### FormField / FormSection
`FormField` wraps label+control+helper+error (used by Input/Select/Textarea internally).
`FormSection` gives auth/modal forms consistent spacing.

### Dropdown / Tabs
`Dropdown` (menu with items, outside-click + Escape close, keyboard arrows) powers the TopBar
user menu. `Tabs` (controlled `value`/`onChange`, `role="tablist"`) available for future
detail pages — adopted only where a real tab UI is needed.

---

## 4. Application shell

### 4.1 Navigation architecture (extensible, data-driven)

Single `navConfig` in `src/lib/nav.js` — groups + items. Groups render as collapsible
sections with uppercase labels; items carry `to`, `label`, optional `roles`. This is the
extensibility seam for the future AI group: **no AI links are added now because no AI routes
exist** (audit decision A-3).

```
CETRAK (brand)
[tenant switcher]
Dashboard
WORKSPACE     Sales · Purchases · Inventory
ACCOUNTING    Accounts · Journal Entries · Reports
MANAGEMENT    Team
```

Module "settings" pages remain reachable from their module group (and from PageHeader where
relevant). Sales/Purchases "Payments" are labeled distinctly ("Payments" vs "Bills").

### 4.2 Sidebar
- `--sidebar-width: 248px`; brand lockup + active tenant; grouped collapsible sections
  (aria `aria-expanded`); clear active state (brand-soft pill + left brand bar);
  hover/active via CSS class; keyboard-operable `NavLink`s with visible focus ring.
- Desktop: persistent, collapsible to a 64px rail (icon-only, tooltips via `title`).
- `< lg` (1024px): becomes a Drawer with overlay, opened from the TopBar; route change
  closes it.
- Logout lives in the TopBar user menu (not duplicated on the dashboard).

### 4.3 TopBar
Sticky, `--bg-surface`, bottom border: mobile nav button (`< lg`), tenant/company switcher
(reusing the existing switch endpoint — no API change), user menu (email + role, dropdown:
**no fake items**), logout. The existing duplicate logout logic in `DashboardPage` is removed.

### 4.4 PageContainer
Single content width (`--content-width: 1200px`, responsive padding) replacing the
720/960/1024px inconsistency. `PageHeader` at top.

---

## 5. Authentication screens

Only **Login** and **Register** (which also serves invitation acceptance via `?token=`)
exist; no forgot/reset routes (decision A-4).

Both use a centered `AuthLayout`: brand lockup, card (`Card`), strong type hierarchy,
`Input` components (label-associated, `aria-invalid`), styled `Checkbox` for remember-me,
password visibility toggle, `Button variant="primary"` with real loading state, `Alert` for
errors, footer links. **Zero changes to `services/api.js`, payloads, CSRF handling, or the
tenant/redirect logic.** Register hides the company field for invitations (unchanged
behavior).

---

## 6. Chart of Accounts — golden reference

`PageHeader` (title "Chart of Accounts", description, primary "Create Account") → tree table.
- Account name with depth indentation + expand/collapse (behavior preserved).
- `AccountingTypeBadge` per row (dot + label — not color-only).
- Status column (`Active`/`Inactive` badge).
- Actions: **Edit** = secondary (ghost/outline), **Deactivate** = danger tone and routed
  through `ConfirmDialog` (replaces `window.confirm`; `alert` failure → toast).
- Controlled width, no viewport overflow; horizontal scroll only if genuinely needed.

This page is the template every ERP page is normalized against.

---

## 7. Responsive design

| Breakpoint | Behavior |
|---|---|
| `≥ 1280px` | full sidebar + wide content |
| `lg 1024–1279px` | collapsed icon rail |
| `md 768–1023px` | drawer navigation |
| `< 768px` | drawer; single-column forms; tables scroll horizontally inside `cetrak-table-scroll`; PageHeader actions stack |

Content never relies on hover alone; tap targets ≥ 32px.

---

## 8. Accessibility

Semantic HTML; every input has an associated label; visible focus ring on all interactive
elements; buttons/links are real elements; `aria-label` on icon-only buttons; `aria-current`
on active nav; status always text+color; modals are `role="dialog"` with focus trap + Escape;
dropdowns close on Escape/outside-click; color contrast meets WCAG AA on both themes.

---

## 9. UX states

Every data view supports loading (Skeleton), empty (EmptyState), error (ErrorState/Alert),
and no-results. No blank screens for "no accounts / invoices / customers / transactions".

---

## 10. Non-functional constraints (hard)

- **No** changes to API endpoints, payloads, response contracts, auth behavior, tenant
  isolation, permissions, or any backend code.
- **No** removal of working functionality; route paths and guards are preserved.
- **No** new framework; **no** Tailwind introduction (audit A-1); **no** AI feature code;
  **no** deployment or push.
- Existing pre-existing lint errors are not hidden by rule changes.
- No frontend test suite exists; gates are `npm run build` + `npm run lint` + visual QA.

---

## 11. Definition of done

Tracked in `frontend-design-system-v1-implementation.md` § checklist; mirrors the brief's
definition of done (audit ✓, tokens ✓, typography ✓, buttons/inputs/selects/badges/tables/
modals/toasts/loading/empty/error states ✓, shell ✓, sidebar scalable ✓, topbar ✓,
login professional ✓, Chart of Accounts polished ✓, behavior intact ✓, build ✓, lint ✓,
responsive reviewed ✓, a11y reviewed ✓, docs ✓, no deploy/push ✓).
