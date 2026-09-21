/**
 * Cetrak design tokens — JS mirror.
 *
 * The app renders with React inline styles; CSS custom properties can be consumed
 * directly via `var(--token)` for static values. This module exists for values that
 * must be resolved to plain strings in JS (e.g. conditional inline styles, charts)
 * and to expose the semantic maps (accounting types, badge tones) as data.
 *
 * Single source of truth is `src/styles/tokens.css`. Keep both in sync.
 */

export const color = {
  bg: {
    app: 'var(--bg-app)',
    surface: 'var(--bg-surface)',
    elevated: 'var(--bg-elevated)',
    hover: 'var(--bg-hover)',
    active: 'var(--bg-active)',
  },
  border: {
    default: 'var(--border)',
    subtle: 'var(--border-subtle)',
    strong: 'var(--border-strong)',
  },
  text: {
    primary: 'var(--text)',
    secondary: 'var(--text-secondary)',
    muted: 'var(--text-muted)',
    disabled: 'var(--text-disabled)',
    inverse: 'var(--text-inverse)',
  },
  brand: {
    primary: 'var(--brand)',
    hover: 'var(--brand-hover)',
    active: 'var(--brand-active)',
    soft: 'var(--brand-soft)',
    foreground: 'var(--brand-foreground)',
  },
  semantic: {
    success: 'var(--success)',
    successSoft: 'var(--success-soft)',
    warning: 'var(--warning)',
    warningSoft: 'var(--warning-soft)',
    danger: 'var(--danger)',
    dangerSoft: 'var(--danger-soft)',
    info: 'var(--info)',
    infoSoft: 'var(--info-soft)',
  },
}

/**
 * Accounting semantic colors — the ONE map for Asset/Liability/Equity/Revenue/Expense.
 * Consumed by AccountRow, reports and any ledger UI. Never re-define per page.
 */
export const accountingTypeTokens = {
  Asset: { fg: 'var(--accounting-asset)', soft: 'var(--accounting-asset-soft)' },
  Liability: { fg: 'var(--accounting-liability)', soft: 'var(--accounting-liability-soft)' },
  Equity: { fg: 'var(--accounting-equity)', soft: 'var(--accounting-equity-soft)' },
  Revenue: { fg: 'var(--accounting-revenue)', soft: 'var(--accounting-revenue-soft)' },
  Expense: { fg: 'var(--accounting-expense)', soft: 'var(--accounting-expense-soft)' },
}

export const font = {
  sans: 'var(--font-sans)',
  mono: 'var(--font-mono)',
  size: {
    display: 'var(--text-display)',
    pageTitle: 'var(--text-page-title)',
    sectionTitle: 'var(--text-section-title)',
    cardTitle: 'var(--text-card-title)',
    body: 'var(--text-body)',
    bodySmall: 'var(--text-body-small)',
    caption: 'var(--text-caption)',
    label: 'var(--text-label)',
  },
  weight: {
    regular: 'var(--weight-regular)',
    medium: 'var(--weight-medium)',
    semibold: 'var(--weight-semibold)',
  },
  leading: {
    tight: 'var(--leading-tight)',
    snug: 'var(--leading-snug)',
    normal: 'var(--leading-normal)',
  },
}

export const space = {
  1: 'var(--space-1)',
  2: 'var(--space-2)',
  3: 'var(--space-3)',
  4: 'var(--space-4)',
  5: 'var(--space-5)',
  6: 'var(--space-6)',
  8: 'var(--space-8)',
  10: 'var(--space-10)',
  12: 'var(--space-12)',
}

export const radius = {
  sm: 'var(--radius-sm)',
  md: 'var(--radius-md)',
  lg: 'var(--radius-lg)',
  pill: 'var(--radius-pill)',
}

export const shadow = {
  xs: 'var(--shadow-xs)',
  sm: 'var(--shadow-sm)',
  md: 'var(--shadow-md)',
  lg: 'var(--shadow-lg)',
}

export const z = {
  dropdown: 'var(--z-dropdown)',
  sticky: 'var(--z-sticky)',
  drawer: 'var(--z-drawer)',
  modal: 'var(--z-modal)',
  toast: 'var(--z-toast)',
}

export const layout = {
  sidebarWidth: 'var(--sidebar-width)',
  sidebarWidthCollapsed: 'var(--sidebar-width-collapsed)',
  topbarHeight: 'var(--topbar-height)',
  contentWidth: 'var(--content-width)',
}
