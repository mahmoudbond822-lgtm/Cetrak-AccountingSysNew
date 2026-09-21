import { useState, useEffect, useCallback } from 'react'
import AccountSelect from '../../components/accounting/journal/AccountSelect'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'
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

export default function PurchasesSettingsPage() {
  const { activeTenantRole } = getAuth()
  const [settings, setSettings] = useState({
    accounts_payable: null,
    expense_account: null,
    input_vat: null,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await purchasesService.getSettings()
      setSettings({
        accounts_payable: data.accounts_payable || null,
        expense_account: data.expense_account || null,
        input_vat: data.input_vat || null,
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
      await purchasesService.updateSettings(settings)
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
        <PageHeader title="Purchases accounting settings" />
        <Card>
          <CardBody>
            <p style={helperStyle}>Only administrators can configure purchase accounting settings.</p>
          </CardBody>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Purchases accounting settings"
        description="Default accounts used when posting purchase invoices."
        breadcrumbs={[{ label: 'Purchases' }, { label: 'Settings' }]}
      />

      <p style={helperStyle}>
        These accounts are used when posting purchase invoices. Only accounts of the matching
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
              <label style={labelStyle}>Accounts Payable (Liability)</label>
              <AccountSelect
                value={settings.accounts_payable}
                onChange={setField('accounts_payable')}
                placeholder="Select Liability account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Expense Account (Expense)</label>
              <AccountSelect
                value={settings.expense_account}
                onChange={setField('expense_account')}
                placeholder="Select Expense account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Input VAT (Asset)</label>
              <AccountSelect
                value={settings.input_vat}
                onChange={setField('input_vat')}
                placeholder="Select Asset account..."
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
