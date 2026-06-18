import { useState } from 'react'

const wrapperStyle = { display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '1.5rem' }
const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.25rem' }
const labelStyle = { fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }
const selectStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none', minWidth: '180px',
}
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const btnPrimary = {
  cursor: 'pointer', background: 'var(--accent)', color: '#fff',
  border: 'none', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem', fontWeight: 500,
}

const REPORT_TYPES = [
  { value: 'trial-balance', label: 'Trial Balance', needsRange: true },
  { value: 'income-statement', label: 'Income Statement', needsRange: true },
  { value: 'balance-sheet', label: 'Balance Sheet', needsRange: false },
]

export default function ReportSelector({ onGenerate }) {
  const [type, setType] = useState('trial-balance')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [asOf, setAsOf] = useState(new Date().toISOString().split('T')[0])

  const currentType = REPORT_TYPES.find((t) => t.value === type)

  function handleGenerate() {
    const params = { type }
    if (currentType.needsRange) {
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
    } else {
      if (asOf) params.as_of = asOf
    }
    onGenerate(params)
  }

  return (
    <div style={wrapperStyle}>
      <div style={fieldStyle}>
        <label style={labelStyle}>Report Type</label>
        <select style={selectStyle} value={type} onChange={(e) => setType(e.target.value)}>
          {REPORT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      {currentType.needsRange ? (
        <>
          <div style={fieldStyle}>
            <label style={labelStyle}>From</label>
            <input style={inputStyle} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle}>To</label>
            <input style={inputStyle} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </>
      ) : (
        <div style={fieldStyle}>
          <label style={labelStyle}>As of</label>
          <input style={inputStyle} type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </div>
      )}
      <button type="button" style={btnPrimary} onClick={handleGenerate}>
        Generate Report
      </button>
    </div>
  )
}
