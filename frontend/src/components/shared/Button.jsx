const variants = {
  primary: { background: 'var(--accent)', color: '#fff', border: 'none' },
  secondary: { background: 'transparent', color: 'var(--text)', border: '1px solid var(--border)' },
  danger: { background: '#F44336', color: '#fff', border: 'none' },
}

const baseStyle = {
  cursor: 'pointer', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem', fontWeight: 500, display: 'inline-flex',
  alignItems: 'center', justifyContent: 'center', gap: '0.375rem',
}

const disabledStyle = { opacity: 0.5, cursor: 'not-allowed' }

export default function Button({ variant = 'primary', disabled, children, style, ...props }) {
  return (
    <button
      style={{ ...baseStyle, ...variants[variant], ...(disabled ? disabledStyle : {}), ...style }}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}
