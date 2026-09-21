import { useState } from 'react'
import { cn } from '../../lib/cn'
import FormField from './FormField'

const controlWrapperStyle = { position: 'relative', width: '100%' }

const affixStyle = {
  position: 'absolute',
  top: 0,
  bottom: 0,
  right: 'var(--space-2)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: 'none',
  background: 'transparent',
  color: 'var(--text-muted)',
  cursor: 'pointer',
  padding: 'var(--space-1)',
  borderRadius: 'var(--radius-sm)',
}

const passwordInputStyle = { paddingRight: 'var(--space-10)' }

function EyeIcon({ open }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {open ? (
        <>
          <path d="M2 12s3.587-7 10-7 10 7 10 7-3.587 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </>
      ) : (
        <>
          <path d="M9.88 9.88a3 3 0 0 0 4.24 4.24" />
          <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c6.413 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
          <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3.587 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
          <line x1="2" y1="2" x2="22" y2="22" />
        </>
      )}
    </svg>
  )
}

/**
 * Input — text/email/password/number/search.
 *
 * Supports label, helperText, error, required, disabled, placeholder, and a
 * password visibility toggle (type="password" only). Label is associated and
 * `aria-invalid` is set when an error is present.
 */
export default function Input({
  label,
  helperText,
  error,
  required,
  disabled,
  type = 'text',
  className,
  style,
  id,
  ...props
}) {
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === 'password'
  const effectiveType = isPassword ? (showPassword ? 'text' : 'password') : type

  const control = (a11y) => (
    <div style={controlWrapperStyle}>
      <input
        id={id || a11y.id}
        type={effectiveType}
        className={cn('cetrak-input', className)}
        style={{
          ...(isPassword ? passwordInputStyle : null),
          ...style,
        }}
        disabled={disabled}
        required={required}
        {...a11y}
        {...props}
      />
      {isPassword && (
        <button
          type="button"
          style={affixStyle}
          onClick={() => setShowPassword((v) => !v)}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          aria-pressed={showPassword}
          className="cetrak-focus-visible"
          tabIndex={disabled ? -1 : 0}
        >
          <EyeIcon open={showPassword} />
        </button>
      )}
    </div>
  )

  if (label || helperText || error) {
    return (
      <FormField label={label} helperText={helperText} error={error} required={required}>
        {control}
      </FormField>
    )
  }
  return control({ id, 'aria-invalid': error ? 'true' : undefined })
}
