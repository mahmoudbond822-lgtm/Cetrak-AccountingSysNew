import { useState } from 'react'

const rowStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.5rem 0',
  borderBottom: '1px solid var(--border)',
  fontSize: '0.875rem',
}

const toggleBtn = {
  cursor: 'pointer',
  background: 'none',
  border: '1px solid var(--border)',
  borderRadius: '4px',
  width: '24px',
  height: '24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '0.75rem',
  flexShrink: 0,
}

const indent = { width: '24px', flexShrink: 0 }

const nameStyle = { flex: 1, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
const typeStyle = { color: 'var(--text)', width: '100px', fontSize: '0.8rem' }
const actionsStyle = { display: 'flex', gap: '0.25rem' }
const actionBtn = {
  cursor: 'pointer', background: 'none', border: '1px solid var(--border)',
  borderRadius: '4px', padding: '0.25rem 0.5rem', fontSize: '0.75rem',
  color: 'var(--text)',
}

const typeColors = {
  Asset: '#4CAF50',
  Liability: '#F44336',
  Equity: '#2196F3',
  Revenue: '#FF9800',
  Expense: '#9C27B0',
}

export default function AccountRow({ account, onEdit, onDeactivate, depth = 0 }) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = account.children && account.children.length > 0

  return (
    <>
      <div style={{ ...rowStyle, paddingLeft: `${depth * 24}px` }}>
        {hasChildren ? (
          <button style={toggleBtn} onClick={() => setExpanded(!expanded)} title={expanded ? 'Collapse' : 'Expand'}>
            {expanded ? '−' : '+'}
          </button>
        ) : (
          <div style={indent} />
        )}
        <span style={{
          ...nameStyle,
          '&:hover': { cursor: 'pointer' },
        }}
          title={account.name}>
          {account.name}
        </span>
        <span style={typeStyle}>
          <span style={{
            display: 'inline-block',
            width: '8px', height: '8px', borderRadius: '50%',
            background: typeColors[account.type] || '#999',
            marginRight: '0.375rem',
          }} />
          {account.type}
        </span>
        <div style={actionsStyle}>
          <button style={actionBtn} onClick={() => onEdit(account)}>Edit</button>
          <button style={actionBtn} onClick={() => onDeactivate(account)}>Deactivate</button>
        </div>
      </div>
      {expanded && hasChildren && account.children.map((child) => (
        <AccountRow key={child.id} account={child} onEdit={onEdit} onDeactivate={onDeactivate} depth={depth + 1} />
      ))}
    </>
  )
}
