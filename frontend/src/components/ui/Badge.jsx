import { cn } from '../../lib/cn'
import { accountingTypeTokens } from '../../lib/tokens'

const toneStyles = {
  neutral: { background: 'var(--bg-hover)', color: 'var(--text-secondary)', border: 'var(--border)' },
  brand: { background: 'var(--brand-soft)', color: 'var(--brand)', border: 'transparent' },
  success: { background: 'var(--success-soft)', color: 'var(--success)', border: 'transparent' },
  warning: { background: 'var(--warning-soft)', color: 'var(--warning)', border: 'transparent' },
  danger: { background: 'var(--danger-soft)', color: 'var(--danger)', border: 'transparent' },
  info: { background: 'var(--info-soft)', color: 'var(--info)', border: 'transparent' },
}

const sizeStyles = {
  sm: { fontSize: '11px', padding: '2px 7px', gap: '5px' },
  md: { fontSize: '12px', padding: '3px 9px', gap: '6px' },
}

const baseStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  borderRadius: 'var(--radius-pill)',
  fontWeight: 600,
  lineHeight: 1.4,
  whiteSpace: 'nowrap',
  borderWidth: '1px',
  borderStyle: 'solid',
}

const dotStyle = {
  width: '6px',
  height: '6px',
  borderRadius: '50%',
  flexShrink: 0,
}

/**
 * Badge — status pill. Text is always present so status is never color-only.
 *
 * Variants: neutral, brand, success, warning, danger, info.
 * `AccountingTypeBadge` maps the five ledger types onto the accounting tokens.
 */
export default function Badge({ tone = 'neutral', size = 'md', dot = false, className, style, children }) {
  const toneStyle = toneStyles[tone] || toneStyles.neutral
  return (
    <span
      className={cn(className)}
      style={{ ...baseStyle, ...toneStyle, ...sizeStyles[size], ...style }}
    >
      {dot && (
        <span
          style={{ ...dotStyle, background: toneStyle.color }}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  )
}

const accountingFallback = { fg: 'var(--text-muted)', soft: 'var(--bg-hover)' }

/**
 * AccountingTypeBadge — the single visual representation of a ledger account type.
 * Uses the global accountingTypeTokens map; unknown types degrade gracefully.
 */
export function AccountingTypeBadge({ type, size = 'md' }) {
  const t = accountingTypeTokens[type] || accountingFallback
  return (
    <Badge
      size={size}
      dot
      style={{ background: t.soft, color: t.fg, border: 'transparent' }}
    >
      {type}
    </Badge>
  )
}
