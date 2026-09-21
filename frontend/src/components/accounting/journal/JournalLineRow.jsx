import AccountSelect from './AccountSelect'

const rowStyle = {
  display: 'grid',
  gridTemplateColumns: '2fr 1fr 1fr 40px',
  gap: '0.5rem',
  alignItems: 'center',
  marginBottom: '0.5rem',
}

const btnRemove = {
  cursor: 'pointer', background: 'none', border: 'none',
  color: 'var(--danger)', fontSize: '1.25rem', padding: '0.25rem',
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
        className="cetrak-input"
        type="number"
        step="0.0001"
        min="0"
        placeholder="0.00"
        aria-label={`Debit (line ${index + 1})`}
        value={line.debit}
        onChange={(e) => {
          const value = e.target.value
          const updatedLine = { ...line, debit: value }
          if (value && parseFloat(value) > 0) updatedLine.credit = ''
          onChange(index, updatedLine)
        }}
        disabled={disabled}
      />
      <input
        className="cetrak-input"
        type="number"
        step="0.0001"
        min="0"
        placeholder="0.00"
        aria-label={`Credit (line ${index + 1})`}
        value={line.credit}
        onChange={(e) => {
          const value = e.target.value
          const updatedLine = { ...line, credit: value }
          if (value && parseFloat(value) > 0) updatedLine.debit = ''
          onChange(index, updatedLine)
        }}
        disabled={disabled}
      />
      <button style={btnRemove} onClick={() => onRemove(index)} disabled={disabled} title="Remove line">
        ×
      </button>
    </div>
  )
}
