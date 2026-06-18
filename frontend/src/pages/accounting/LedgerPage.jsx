import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import AccountingNav from '../../components/Layout/AccountingNav'
import LedgerTable from '../../components/accounting/ledger/LedgerTable'
import { accountingService } from '../../services/accountingService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const filterStyle = { display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem' }
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}
const accountHeaderStyle = {
  padding: '1rem', background: '#f9f9f9', borderRadius: '8px',
  border: '1px solid var(--border)', marginBottom: '1rem',
}

export default function LedgerPage() {
  const { accountId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  async function fetchLedger() {
    setLoading(true)
    setError('')
    try {
      const params = { account_id: accountId }
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const { data: result } = await accountingService.getLedger(params)
      setData(result)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load ledger.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLedger() }, [accountId])

  return (
    <div>
      <AccountingNav />
      <div style={pageStyle}>
        <h1 style={titleStyle}>General Ledger</h1>

        <div style={filterStyle}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text)' }}>From:</label>
          <input style={inputStyle} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <label style={{ fontSize: '0.8rem', color: 'var(--text)' }}>To:</label>
          <input style={inputStyle} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <button
            type="button"
            style={{
              cursor: 'pointer', background: 'var(--accent)', color: '#fff',
              border: 'none', borderRadius: '6px', padding: '0.5rem 1rem',
              fontSize: '0.875rem',
            }}
            onClick={fetchLedger}
          >
            Filter
          </button>
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>{[...Array(5)].map((_, i) => <div key={i} style={skeletonStyle} />)}</div>
        ) : data ? (
          <>
            <div style={accountHeaderStyle}>
              <div style={{ fontSize: '1rem', fontWeight: 600 }}>{data.account.name}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text)' }}>Type: {data.account.type}</div>
            </div>
            <LedgerTable entries={data.entries} totals={data.totals} />
          </>
        ) : null}
      </div>
    </div>
  )
}
