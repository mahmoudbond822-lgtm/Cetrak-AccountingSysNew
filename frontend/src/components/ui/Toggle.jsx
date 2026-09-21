import { useId } from 'react'
import { cn } from '../../lib/cn'
import { color, font } from '../../lib/tokens'

const wrapperStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2)',
  cursor: 'pointer',
}

const trackStyle = (checked) => ({
  position: 'relative',
  width: '38px',
  height: '22px',
  borderRadius: 'var(--radius-pill)',
  background: checked ? color.brand.primary : 'var(--bg-active)',
  border: `1px solid ${checked ? color.brand.primary : 'var(--border-strong)'}`,
  flexShrink: 0,
  transition: 'background-color 140ms ease, border-color 140ms ease',
})

const thumbStyle = (checked) => ({
  position: 'absolute',
  top: '2px',
  left: checked ? '19px' : '2px',
  width: '16px',
  height: '16px',
  borderRadius: '50%',
  background: checked ? color.brand.foreground : color.bg.surface,
  transition: 'left 140ms ease',
  boxShadow: 'var(--shadow-xs)',
})

const labelStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.primary,
  cursor: 'pointer',
  userSelect: 'none',
}

/**
 * Toggle — switch control (`role="switch"`).
 */
export default function Toggle({
  label,
  checked,
  defaultChecked = false,
  disabled = false,
  className,
  id,
  ...props
}) {
  const generatedId = useId()
  const inputId = id || generatedId
  const isOn = checked ?? defaultChecked

  return (
    <div
      className={cn(className)}
      style={{ ...wrapperStyle, ...(disabled ? { cursor: 'not-allowed', opacity: 0.5 } : null) }}
    >
      <button
        type="button"
        id={inputId}
        role="switch"
        aria-checked={isOn}
        className="cetrak-toggle cetrak-focus-visible"
        style={trackStyle(isOn)}
        disabled={disabled}
        {...props}
      >
        <span style={thumbStyle(isOn)} aria-hidden="true" />
      </button>
      {label && (
        <label style={labelStyle} htmlFor={inputId}>
          {label}
        </label>
      )}
    </div>
  )
}
