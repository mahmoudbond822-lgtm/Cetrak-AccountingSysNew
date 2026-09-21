import { useState, useEffect, useRef } from 'react'
import { accountingService } from '../../../services/accountingService'
import { color, font, space } from '../../../lib/tokens'
import { AccountingTypeBadge } from '../../ui'

const wrapperStyle = { position: 'relative' }

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
}

const dropdownStyle = {
  position: 'absolute',
  top: '100%',
  left: 0,
  right: 0,
  background: color.bg.elevated,
  border: `1px solid ${color.border.default}`,
  borderRadius: 'var(--radius-md)',
  maxHeight: '220px',
  overflowY: 'auto',
  zIndex: 'var(--z-dropdown)',
  boxShadow: 'var(--shadow-md)',
  padding: `${space[1]} 0`,
}

const optionStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: space[2],
  width: '100%',
  textAlign: 'left',
  padding: `${space[2]} ${space[3]}`,
  cursor: 'pointer',
  fontSize: font.size.bodySmall,
  color: color.text.primary,
  background: 'none',
  border: 'none',
}

const optionSelectedStyle = { background: color.brand.soft }

const selectedValueStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: space[2],
  width: '100%',
  boxSizing: 'border-box',
  padding: `0 ${space[3]}`,
  height: '38px',
  border: `1px solid ${color.border.default}`,
  borderRadius: 'var(--radius-sm)',
  background: color.bg.surface,
  color: color.text.primary,
  fontSize: font.size.body,
  cursor: 'pointer',
  textAlign: 'left',
}

const placeholderStyle = { color: color.text.muted }

/**
 * AccountSelect — searchable account picker (combobox).
 *
 * Used by the sales/purchases settings pages. Options are real buttons so the
 * control is keyboard-operable; styling comes from the token system so it works
 * in both light and dark themes.
 */
export default function AccountSelect({ value, onChange, placeholder = 'Search accounts...' }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(false)
  const wrapperRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    accountingService.getAccounts().then(({ data }) => {
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
        <button
          type="button"
          style={selectedValueStyle}
          className="cetrak-focus-visible"
          onClick={() => { setOpen(true); setQuery('') }}
          aria-haspopup="listbox"
          aria-expanded={false}
        >
          <span style={selected ? null : placeholderStyle}>
            {selected ? `${selected.name} (${selected.type})` : placeholder}
          </span>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
            style={{ flexShrink: 0, color: color.text.muted }}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      ) : (
        <>
          <input
            className="cetrak-input"
            style={inputStyle}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search..."
            autoFocus
            aria-label="Search accounts"
            role="combobox"
            aria-expanded="true"
            aria-controls="account-select-list"
          />
          <div style={dropdownStyle} role="listbox" id="account-select-list">
            {loading ? (
              <div style={{ padding: `${space[2]} ${space[3]}`, fontSize: font.size.bodySmall, color: color.text.muted }}>
                Loading accounts…
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: `${space[2]} ${space[3]}`, fontSize: font.size.bodySmall, color: color.text.muted }}>
                No accounts found
              </div>
            ) : (
              filtered.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  role="option"
                  aria-selected={a.id === value}
                  style={{ ...optionStyle, ...(a.id === value ? optionSelectedStyle : null) }}
                  className="cetrak-focus-visible"
                  onClick={() => { onChange(a.id); setOpen(false); setQuery('') }}
                >
                  <span>{a.name}</span>
                  <AccountingTypeBadge type={a.type} size="sm" />
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}
