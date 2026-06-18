const wrapperStyle = { display: 'flex', flexDirection: 'column', gap: '0.25rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none', width: '100%',
  boxSizing: 'border-box',
}
const errorStyle = { fontSize: '0.75rem', color: '#F44336' }

export default function Input({ label, error, style, ...props }) {
  return (
    <div style={{ ...wrapperStyle, ...style }}>
      {label && <label style={labelStyle}>{label}</label>}
      <input
        style={{ ...inputStyle, borderColor: error ? '#F44336' : 'var(--border)' }}
        {...props}
      />
      {error && <span style={errorStyle}>{error}</span>}
    </div>
  )
}
