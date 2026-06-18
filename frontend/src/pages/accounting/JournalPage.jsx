import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import AccountingNav from '../../components/Layout/AccountingNav'
import JournalEntryForm from '../../components/accounting/journal/JournalEntryForm'
import { accountingService } from '../../services/accountingService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const headerStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600 }
const btnPrimary = {
  cursor: 'pointer', background: 'var(--accent)', color: '#fff',
  border: 'none', borderRadius: '6px', padding: '0.5rem 1rem',
  fontSize: '0.875rem', fontWeight: 500, textDecoration: 'none',
}
const filterStyle = { display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem' }
const inputStyle = {
  padding: '0.5rem 0.75rem', border: '1px solid var(--border)',
  borderRadius: '6px', fontSize: '0.875rem', outline: 'none',
}
const rowStyle = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)',
  cursor: 'pointer', fontSize: '0.875rem',
}
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

export default function JournalPage() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showForm, setShowForm] = useState(false)

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = {}
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const { data } = await accountingService.getJournalEntries(params)
      setEntries(data)
    } catch (err) {
      setError('Failed to load journal entries.')
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo])

  useEffect(() => { fetchEntries() }, [fetchEntries])

  function handleSaved() {
    setShowForm(false)
    fetchEntries()
  }

  if (showForm) {
    return (
      <div>
        <AccountingNav />
        <div style={pageStyle}>
          <JournalEntryForm onSaved={handleSaved} onCancel={() => setShowForm(false)} />
        </div>
      </div>
    )
  }

  return (
    <div>
      <AccountingNav />
      <div style={pageStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>Journal Entries</h1>
          <button style={btnPrimary} onClick={() => setShowForm(true)}>
            + New Entry
          </button>
        </div>

        <div style={filterStyle}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text)' }}>From:</label>
          <input style={inputStyle} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <label style={{ fontSize: '0.8rem', color: 'var(--text)' }}>To:</label>
          <input style={inputStyle} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          {(dateFrom || dateTo) && (
            <button style={{ ...btnPrimary, background: 'transparent', color: 'var(--text)', border: '1px solid var(--border)' }} onClick={() => { setDateFrom(''); setDateTo('') }}>
              Clear
            </button>
          )}
        </div>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>{[...Array(5)].map((_, i) => <div key={i} style={skeletonStyle} />)}</div>
        ) : entries.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text)' }}>
            No journal entries found. Create your first entry to get started.
          </div>
        ) : (
          <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden' }}>
            {entries.map((entry) => (
              <div key={entry.id} style={rowStyle}>
                <div>
                  <div style={{ fontWeight: 500 }}>{entry.reference}</div>
                  <div style={{ color: 'var(--text)', fontSize: '0.8rem' }}>{entry.date}</div>
                </div>
                <div style={{ flex: 1, margin: '0 1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {entry.description}
                </div>
                <div style={{ textAlign: 'right', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                  <div>Dr {parseFloat(entry.total_debit).toFixed(2)}</div>
                  <div>Cr {parseFloat(entry.total_credit).toFixed(2)}</div>
                </div>
                <div style={{ marginLeft: '1rem', fontSize: '0.75rem', color: 'var(--text)' }}>
                  {entry.line_count} lines
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
