import { useEffect } from 'react'

const overlayStyle = {
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center',
  justifyContent: 'center', zIndex: 1000,
}
const cardStyle = {
  background: '#fff', borderRadius: '12px', padding: '1.5rem',
  minWidth: '400px', maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto',
  boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
}
const headerStyle = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  marginBottom: '1rem', fontSize: '1.125rem', fontWeight: 600,
}
const closeBtn = {
  cursor: 'pointer', background: 'none', border: 'none',
  fontSize: '1.25rem', color: 'var(--text)', padding: '0.25rem',
}
const footerStyle = {
  display: 'flex', justifyContent: 'flex-end', gap: '0.5rem',
  marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)',
}

export default function Modal({ open, onClose, title, children, footer }) {
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape' && open) onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div style={cardStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>{title}</span>
          <button style={closeBtn} onClick={onClose}>×</button>
        </div>
        {children}
        {footer && <div style={footerStyle}>{footer}</div>}
      </div>
    </div>
  )
}
