import AccountSelect from './AccountSelect'

const rowStyle = {
  display: 'grid',
  gridTemplateColumns: '2fr 1fr 1fr 40px',
  gap: '0.5rem',
  alignItems: 'center',
  marginBottom: '0.5rem',
}

const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none', width: '100%',
  boxSizing: 'border-box',
}

const btnRemove = {
  cursor: 'pointer', background: 'none', border: 'none',
  color: '#F44336', fontSize: '1.25rem', padding: '0.25rem',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}

export default function JournalLineRow({ line, index, onChange, onRemove, disabled }) {
  function handleField(field, value) {
    onChange(index, { ...line, [field]: value })
  }

  return (
    <div style={rowStyle}>
      <AccountSelect
        value={line.account_id}
        onChange={(id) => handleField('account_id', id)}
        placeholder="Select account..."
      />
      <input
        style={inputStyle}
        type="number"
        step="0.0001"
        min="0"
        placeholder="0.00"
        value={line.debit}
        onChange={(e) => {
          handleField('debit', e.target.value)
          if (e.target.value && parseFloat(e.target.value) > 0) handleField('credit', '')
        }}
        disabled={disabled}
      />
      <input
        style={inputStyle}
        type="number"
        step="0.0001"
        min="0"
        placeholder="0.00"
        value={line.credit}
        onChange={(e) => {
          handleField('credit', e.target.value)
          if (e.target.value && parseFloat(e.target.value) > 0) handleField('debit', '')
        }}
        disabled={disabled}
      />
      <button style={btnRemove} onClick={() => onRemove(index)} disabled={disabled} title="Remove line">
        ×
      </button>
    </div>
  )
}
