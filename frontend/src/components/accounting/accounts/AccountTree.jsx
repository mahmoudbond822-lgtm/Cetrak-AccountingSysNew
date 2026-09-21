import AccountRow from './AccountRow'
import { color, space } from '../../../lib/tokens'

const containerStyle = {
  border: `1px solid ${color.border.default}`,
  borderRadius: 'var(--radius-md)',
  overflow: 'hidden',
  background: color.bg.surface,
}

const scrollWrapperStyle = {
  width: '100%',
  overflowX: 'auto',
  WebkitOverflowScrolling: 'touch',
}

const headerStyle = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) 132px 120px 128px',
  alignItems: 'center',
  gap: space[3],
  padding: `${space[3]} ${space[4]}`,
  background: color.bg.hover,
  borderBottom: `1px solid ${color.border.default}`,
  fontSize: 'var(--text-caption)',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  color: color.text.muted,
}

const headerActionsStyle = {
  textAlign: 'right',
}

export default function AccountTree({ accounts, onEdit, onDeactivate }) {
  return (
    <div className="cetrak-scroll" style={scrollWrapperStyle}>
      <div style={containerStyle}>
      <div
        style={headerStyle}
        role="row"
        aria-label="Account list columns"
      >
        <span role="columnheader">Account name</span>
        <span role="columnheader">Type</span>
        <span role="columnheader">Status</span>
        <span role="columnheader" style={headerActionsStyle}>Actions</span>
      </div>
      <div>
        {accounts.length === 0 ? null : (
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
    </div>
  )
}