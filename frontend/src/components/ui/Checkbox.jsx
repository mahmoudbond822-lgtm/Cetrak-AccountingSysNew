import { useId } from 'react'
import { cn } from '../../lib/cn'
import { color, font } from '../../lib/tokens'

const wrapperStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2)',
  cursor: 'pointer',
}

const wrapperDisabledStyle = { cursor: 'not-allowed', opacity: 0.5 }

const boxStyle = {
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
 * Checkbox — associated label, indeterminate support, keyboard/focus via native input.
 */
export default function Checkbox({
  label,
  checked,
  defaultChecked,
  indeterminate = false,
  disabled = false,
  required = false,
  className,
  id,
  ...props
}) {
  const generatedId = useId()
  const inputId = id || generatedId

  return (
    <div
      className={cn(className)}
      style={{ ...wrapperStyle, ...(disabled ? wrapperDisabledStyle : null) }}
    >
      <input
        id={inputId}
        type="checkbox"
        className="cetrak-checkbox"
        style={boxStyle}
        checked={checked}
        defaultChecked={defaultChecked}
        ref={(el) => {
          if (el) el.indeterminate = indeterminate
        }}
        disabled={disabled}
        required={required}
        {...props}
      />
      {label && (
        <label style={labelStyle} htmlFor={inputId}>
          {label}
          {required && <span style={{ color: color.semantic.danger, marginLeft: '2px' }} aria-hidden="true">*</span>}
        </label>
      )}
    </div>
  )
}
