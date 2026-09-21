import { useId } from 'react'
import { color, font, space } from '../../lib/tokens'

const wrapperStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[2],
}

const labelStyle = {
  fontSize: font.size.label,
  fontWeight: font.weight.medium,
  color: color.text.primary,
}

const requiredMarkStyle = {
  color: color.semantic.danger,
  marginLeft: space[1],
}

const helperStyle = {
  fontSize: font.size.caption,
  color: color.text.muted,
}

const errorStyle = {
  fontSize: font.size.caption,
  color: color.semantic.danger,
}

/**
 * FormField — label + control + helper/error wrapper.
 *
 * Associates the label with the control via a generated id (passed to the control
 * as `id`), and wires `aria-invalid` / `aria-describedby` for screen readers.
 * Used internally by Input / Select / Textarea.
 */
export default function FormField({
  label,
  helperText,
  error,
  required,
  children,
  className,
  style,
}) {
  const fieldId = useId()
  const helperId = `${fieldId}-helper`
  const errorId = `${fieldId}-error`
  const describedBy = error ? errorId : helperText ? helperId : undefined

  return (
    <div className={className} style={{ ...wrapperStyle, ...style }}>
      {label && (
        <label style={labelStyle} htmlFor={fieldId}>
          {label}
          {required && <span style={requiredMarkStyle} aria-hidden="true">*</span>}
        </label>
      )}
      {typeof children === 'function'
        ? children({
            id: fieldId,
            'aria-invalid': error ? 'true' : undefined,
            'aria-describedby': describedBy,
          })
        : children}
      {error ? (
        <span id={errorId} style={errorStyle} role="alert">
          {error}
        </span>
      ) : (
        helperText && <span id={helperId} style={helperStyle}>{helperText}</span>
      )}
    </div>
  )
}
