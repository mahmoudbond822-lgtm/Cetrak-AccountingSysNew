import AccountRow from './AccountRow'

const containerStyle = {
  border: '1px solid var(--border)',
  borderRadius: '8px',
  overflow: 'hidden',
}

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1rem',
  background: '#f9f9f9',
  borderBottom: '1px solid var(--border)',
  fontWeight: 600,
  fontSize: '0.8rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--text)',
}

const typeHeader = { width: '100px', textAlign: 'left' }
const actionHeader = { textAlign: 'right', flex: 1 }

export default function AccountTree({ accounts, onEdit, onDeactivate }) {
  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={{ width: '48px' }} />
        <span style={{ flex: 1 }}>Account Name</span>
        <span style={typeHeader}>Type</span>
        <span style={actionHeader}>Actions</span>
      </div>
      <div style={{ padding: '0 1rem' }}>
        {accounts.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)' }}>
            No accounts yet. Create your first account to get started.
          </div>
        ) : (
          accounts.map((account) => (
            <AccountRow
              key={account.id}
              account={account}
              onEdit={onEdit}
              onDeactivate={onDeactivate}
              depth={0}
            />
          ))
        )}
      </div>
    </div>
  )
}
