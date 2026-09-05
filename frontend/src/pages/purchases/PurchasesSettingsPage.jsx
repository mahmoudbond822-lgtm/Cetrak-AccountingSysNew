import { useState, useEffect, useCallback } from 'react'
import PurchasesNav from '../../components/Layout/PurchasesNav'
import Button from '../../components/shared/Button'
import AccountSelect from '../../components/accounting/journal/AccountSelect'
import { getAuth } from '../../services/api'
import { purchasesService } from '../../services/purchasesService'

const pageStyle = { maxWidth: '720px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1.25rem' }
const labelStyle = { fontSize: '0.875rem', fontWeight: 500 }

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

  const fetchSettings = useCallback(() => {
    purchasesService.getSettings()
      .then(({ data }) => setSettings({
        accounts_payable: data.accounts_payable || null,
        expense_account: data.expense_account || null,
        input_vat: data.input_vat || null,
      }))
      .catch(() => setError('Failed to load settings.'))
      .finally(() => setLoading(false))
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
      <div>
        <PurchasesNav />
        <div style={pageStyle}>
          <p>Only administrators can configure purchases accounting settings.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <PurchasesNav />
      <div style={pageStyle}>
        <h1 style={titleStyle}>Purchases Accounting Settings</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text)', marginBottom: '1.5rem' }}>
          These accounts are used when posting purchase invoices. Only accounts of the
          matching type can be selected. Posting is disabled until the required accounts
          are mapped.
        </p>

        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FFF3F3', border: '1px solid #F44336', borderRadius: '6px', marginBottom: '1rem', color: '#F44336', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div style={{ color: 'var(--text)', fontSize: '0.875rem' }}>Loading...</div>
        ) : (
          <div>
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
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <Button variant="primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save Settings'}
              </Button>
              {saved && <span style={{ color: '#2E7D32', fontSize: '0.875rem' }}>Saved.</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}