import { useState } from 'react'
import { Button, Input, Select } from '../../ui'
import { space } from '../../../lib/tokens'

const wrapperStyle = {
  display: 'flex',
  gap: space[3],
  alignItems: 'flex-end',
  flexWrap: 'wrap',
  marginBottom: space[4],
}

const fieldStyle = { minWidth: '170px' }

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
        <Select
          label="Report type"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          {REPORT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </Select>
      </div>
      {currentType.needsRange ? (
        <>
          <div style={fieldStyle}>
            <Input
              label="From"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div style={fieldStyle}>
            <Input
              label="To"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </>
      ) : (
        <div style={fieldStyle}>
          <Input
            label="As of"
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
          />
        </div>
      )}
      <Button variant="primary" onClick={handleGenerate}>Generate Report</Button>
    </div>
  )
}
