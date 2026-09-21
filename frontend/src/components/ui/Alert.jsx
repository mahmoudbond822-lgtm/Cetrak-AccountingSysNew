import { color, font, radius, space } from '../../lib/tokens'
import { cn } from '../../lib/cn'

const toneStyles = {
  error: {
    container: { background: color.semantic.dangerSoft, borderColor: color.semantic.danger, color: color.semantic.danger },
  },
  success: {
    container: { background: color.semantic.successSoft, borderColor: color.semantic.success, color: color.semantic.success },
  },
  warning: {
    container: { background: color.semantic.warningSoft, borderColor: color.semantic.warning, color: color.semantic.warning },
  },
  info: {
    container: { background: color.semantic.infoSoft, borderColor: color.semantic.info, color: color.semantic.info },
  },
}

const baseStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: space[3],
  padding: `${space[3]} ${space[4]}`,
  borderRadius: radius.sm,
  borderWidth: '1px',
  borderStyle: 'solid',
  fontSize: font.size.bodySmall,
  color: color.text.primary,
}

const iconStyle = { flexShrink: 0, marginTop: '1px' }
const contentStyle = { flex: 1, minWidth: 0 }
const titleStyle = { fontWeight: font.weight.semibold, marginBottom: '2px' }
const closeButtonStyle = {
  flexShrink: 0,
  border: 'none',
  background: 'transparent',
  color: 'currentColor',
  cursor: 'pointer',
  padding: '2px',
  borderRadius: radius.sm,
  opacity: 0.7,
  display: 'inline-flex',
}

const icons = {
  error: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  ),
  success: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  ),
  warning: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
  info: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  ),
}

/**
 * Alert — inline banner for form/page feedback.
 *
 * Replaces the 14 duplicated inline error banners and 5 success banners.
 * Text + icon convey the tone, never color alone.
 */
export default function Alert({
  tone = 'info',
  title,
  dismissible = false,
  onDismiss,
  className,
  style,
  children,
}) {
  const toneStyle = toneStyles[tone] || toneStyles.info

  return (
    <div
      className={cn(className)}
      role={tone === 'error' ? 'alert' : 'status'}
      style={{ ...baseStyle, ...toneStyle.container, ...style }}
    >
      <span style={iconStyle}>{icons[tone]}</span>
      <div style={contentStyle}>
        {title && <div style={titleStyle}>{title}</div>}
        {children}
      </div>
      {dismissible && (
        <button
          type="button"
          style={closeButtonStyle}
          onClick={onDismiss}
          aria-label="Dismiss"
          className="cetrak-focus-visible"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}
