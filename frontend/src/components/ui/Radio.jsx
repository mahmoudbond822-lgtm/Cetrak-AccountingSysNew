import { cn } from '../../lib/cn'
import { color, font } from '../../lib/tokens'

const wrapperStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2)',
  cursor: 'pointer',
}

const inputStyle = {
  width: '16px',
  height: '16px',
  flexShrink: 0,
  accentColor: color.brand.primary,
  cursor: 'pointer',
}

const labelStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.primary,
  cursor: 'pointer',
  userSelect: 'none',
}

/**
 * Radio — single option. Use inside a fieldset/legend or with an associated label.
 */
export default function Radio({ label, disabled = false, className, id, ...props }) {
  return (
    <div
      className={cn(className)}
      style={{ ...wrapperStyle, ...(disabled ? { cursor: 'not-allowed', opacity: 0.5 } : null) }}
    >
      <input
        id={id}
        type="radio"
        className="cetrak-checkbox"
        style={inputStyle}
        disabled={disabled}
        {...props}
      />
      {label && (
        <label style={labelStyle} htmlFor={id}>
          {label}
        </label>
      )}
    </div>
  )
}
