import { useState } from 'react'
import ReportSelector from '../../components/accounting/reports/ReportSelector'
import ReportTable from '../../components/accounting/reports/ReportTable'
import { accountingService } from '../../services/accountingService'
import {
  Alert, Card, CardBody, EmptyState, PageContainer, PageHeader, Skeleton,
} from '../../components/ui'
import { space } from '../../lib/tokens'

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
    <PageContainer>
      <PageHeader
        title="Financial Reports"
        description="Generate trial balance, income statement and balance sheet reports."
        breadcrumbs={[{ label: 'Accounting' }, { label: 'Reports' }]}
      />

      <ReportSelector onGenerate={handleGenerate} />

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardBody>
            <Skeleton count={6} height="36px" />
          </CardBody>
        </Card>
      ) : data ? (
        <Card>
          <CardBody>
            <ReportTable data={data} />
          </CardBody>
        </Card>
      ) : (
        <EmptyState
          title="No report generated"
          description="Select a report type and date range, then click Generate Report."
        />
      )}
    </PageContainer>
  )
}
