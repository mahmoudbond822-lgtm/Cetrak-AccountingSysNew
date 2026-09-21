import { useState, useEffect, useCallback } from 'react'
import AccountSelect from '../../components/accounting/journal/AccountSelect'
import { getAuth } from '../../services/api'
import { salesService } from '../../services/salesService'
import {
  Alert, Button, Card, CardBody, PageContainer, PageHeader, Skeleton,
} from '../../components/ui'
import { font, space } from '../../lib/tokens'

const fieldStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[2],
  marginBottom: space[5],
}

const labelStyle = {
  fontSize: font.size.label,
  fontWeight: font.weight.medium,
}

const helperStyle = {
  fontSize: font.size.bodySmall,
  color: 'var(--text-muted)',
  marginBottom: space[5],
}

export default function SalesSettingsPage() {
  const { activeTenantRole } = getAuth()
  const [settings, setSettings] = useState({
    accounts_receivable: null,
    sales_revenue: null,
    vat_payable: null,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await salesService.getSettings()
      setSettings({
        accounts_receivable: data.accounts_receivable || null,
        sales_revenue: data.sales_revenue || null,
        vat_payable: data.vat_payable || null,
      })
    } catch {
      setError('Failed to load settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchSettings() }, [fetchSettings])

  function setField(field) {
    return (value) => {
      setSettings((prev) => ({ ...prev, [field]: value || null }))
      setSaved(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    setError('')
    try {
      await salesService.updateSettings(settings)
      setSaved(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  if (activeTenantRole !== 'Admin') {
    return (
      <PageContainer>
        <PageHeader title="Sales accounting settings" />
        <Card>
          <CardBody>
            <p style={helperStyle}>Only administrators can configure sales accounting settings.</p>
          </CardBody>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Sales accounting settings"
        description="Default accounts used when posting sales invoices."
        breadcrumbs={[{ label: 'Sales' }, { label: 'Settings' }]}
      />

      <p style={helperStyle}>
        These accounts are used when posting sales invoices. Only accounts of the matching
        type can be selected. Posting is disabled until all required accounts are mapped.
      </p>

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardBody>
            <Skeleton count={3} height="38px" />
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardBody>
            <div style={fieldStyle}>
              <label style={labelStyle}>Accounts Receivable (Asset)</label>
              <AccountSelect
                value={settings.accounts_receivable}
                onChange={setField('accounts_receivable')}
                placeholder="Select Asset account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Sales Revenue (Revenue)</label>
              <AccountSelect
                value={settings.sales_revenue}
                onChange={setField('sales_revenue')}
                placeholder="Select Revenue account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>VAT Payable (Liability)</label>
              <AccountSelect
                value={settings.vat_payable}
                onChange={setField('vat_payable')}
                placeholder="Select Liability account..."
              />
            </div>
            <div style={{ display: 'flex', gap: space[3], alignItems: 'center' }}>
              <Button variant="primary" onClick={handleSave} loading={saving}>
                {saving ? 'Saving…' : 'Save settings'}
              </Button>
              {saved && (
                <Alert tone="success" style={{ marginBottom: 0 }}>Saved.</Alert>
              )}
            </div>
          </CardBody>
        </Card>
      )}
    </PageContainer>
  )
}
