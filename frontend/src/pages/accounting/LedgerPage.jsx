import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import LedgerTable from '../../components/accounting/ledger/LedgerTable'
import { accountingService } from '../../services/accountingService'
import {
  Alert, Button, Card, Input, PageContainer, PageHeader, Skeleton,
} from '../../components/ui'
import { color, font, space } from '../../lib/tokens'

const filterStyle = {
  display: 'flex',
  gap: space[3],
  alignItems: 'flex-end',
  marginBottom: space[4],
  flexWrap: 'wrap',
}

const accountHeaderStyle = {
  padding: space[4],
  background: color.bg.hover,
  borderRadius: 'var(--radius-md)',
  border: `1px solid ${color.border.default}`,
  marginBottom: space[4],
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
    <PageContainer>
      <PageHeader
        title="General Ledger"
        description="All postings for a single account."
        breadcrumbs={[{ label: 'Accounting' }, { label: 'General Ledger' }]}
      />

      <div style={filterStyle}>
        <Input
          label="From"
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          style={{ width: '170px' }}
        />
        <Input
          label="To"
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          style={{ width: '170px' }}
        />
        <Button variant="primary" onClick={fetchLedger}>Filter</Button>
        {(dateFrom || dateTo) && (
          <Button variant="ghost" onClick={() => { setDateFrom(''); setDateTo('') }}>
            Clear
          </Button>
        )}
      </div>

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: space[2] }} aria-busy="true">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} height="44px" />
          ))}
        </div>
      ) : data ? (
        <>
          <div style={accountHeaderStyle}>
            <div style={{ fontSize: font.size.cardTitle, fontWeight: font.weight.semibold, color: color.text.primary }}>
              {data.account.name}
            </div>
            <div style={{ fontSize: font.size.caption, color: color.text.muted, marginTop: space[1] }}>
              Type: {data.account.type}
            </div>
          </div>
          <Card>
            <LedgerTable entries={data.entries} totals={data.totals} />
          </Card>
        </>
      ) : null}
    </PageContainer>
  )
}
