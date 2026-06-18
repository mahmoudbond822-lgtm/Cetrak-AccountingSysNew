import { useState, useEffect, useRef } from 'react'
import api from '../../services/api'

const wrapperStyle = { position: 'relative' }
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
const dropdownStyle = {
  position: 'absolute', top: '100%', left: 0, right: 0,
  background: '#fff', border: '1px solid var(--border)',
  borderRadius: '6px', maxHeight: '200px', overflowY: 'auto',
  zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
}
const optionStyle = {
  padding: '0.5rem 0.75rem', cursor: 'pointer',
  fontSize: '0.875rem', borderBottom: '1px solid var(--border)',
}
const selectedValueStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', cursor: 'pointer',
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  background: '#fff', minHeight: '20px',
}

export default function AccountSelect({ value, onChange, placeholder = 'Search accounts...' }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const wrapperRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    api.get('/accounting/accounts/').then(({ data }) => {
      setAccounts(data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    function handleClick(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const filtered = query
    ? accounts.filter((a) => a.name.toLowerCase().includes(query.toLowerCase()))
    : accounts

  const selected = accounts.find((a) => a.id === value)

  return (
    <div ref={wrapperRef} style={wrapperStyle}>
      {!open ? (
        <div style={selectedValueStyle} onClick={() => { setOpen(true); setQuery('') }}>
          {selected ? `${selected.name} (${selected.type})` : placeholder}
          <span style={{ fontSize: '0.7rem' }}>▼</span>
        </div>
      ) : (
        <>
          <input
            style={inputStyle}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search..."
            autoFocus
          />
          <div style={dropdownStyle}>
            {loading ? (
              <div style={{ padding: '0.5rem', textAlign: 'center', color: 'var(--text)' }}>Loading...</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '0.5rem', textAlign: 'center', color: 'var(--text)' }}>No accounts found</div>
            ) : (
              filtered.map((a) => (
                <div
                  key={a.id}
                  style={{ ...optionStyle, background: a.id === value ? '#f0f0ff' : 'transparent' }}
                  onClick={() => { onChange(a.id); setOpen(false); setQuery('') }}
                >
                  {a.name}
                  <span style={{ color: 'var(--text)', fontSize: '0.75rem', marginLeft: '0.5rem' }}>({a.type})</span>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}
