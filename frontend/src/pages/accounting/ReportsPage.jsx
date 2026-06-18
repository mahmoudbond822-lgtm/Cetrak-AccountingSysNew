import { useState } from 'react'
import AccountingNav from '../../components/Layout/AccountingNav'
import ReportSelector from '../../components/accounting/reports/ReportSelector'
import ReportTable from '../../components/accounting/reports/ReportTable'
import { accountingService } from '../../services/accountingService'

const pageStyle = { maxWidth: '960px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const skeletonStyle = {
  height: '40px', background: '#f0f0f0', borderRadius: '6px',
  marginBottom: '0.5rem',
}

export default function ReportsPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleGenerate(params) {
    setLoading(true)
    setError('')
    setData(null)
    try {
      const { type, ...queryParams } = params
      const endpoint = type === 'trial-balance'
        ? accountingService.getTrialBalance
        : type === 'income-statement'
          ? accountingService.getIncomeStatement
          : accountingService.getBalanceSheet
      const { data: result } = await endpoint(queryParams)
      setData(result)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <AccountingNav />
      <div style={pageStyle}>
        <h1 style={titleStyle}>Financial Reports</h1>

        <ReportSelector onGenerate={handleGenerate} />

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>{[...Array(5)].map((_, i) => <div key={i} style={skeletonStyle} />)}</div>
        ) : (
          <ReportTable data={data} />
        )}
      </div>
    </div>
  )
}
