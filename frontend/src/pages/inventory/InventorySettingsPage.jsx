import { useState, useEffect, useCallback } from 'react'
import InventoryNav from '../../components/Layout/InventoryNav'
import Button from '../../components/shared/Button'
import AccountSelect from '../../components/accounting/journal/AccountSelect'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'

const pageStyle = { maxWidth: '720px', margin: '0 auto', padding: '1.5rem' }
const titleStyle = { fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }
const fieldStyle = { display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1.25rem' }
const labelStyle = { fontSize: '0.875rem', fontWeight: 500 }

export default function InventorySettingsPage() {
  const { activeTenantRole } = getAuth()
  const [settings, setSettings] = useState({
    inventory_account: null,
    cogs_account: null,
    adjustments_account: null,
    default_warehouse: null,
  })
  const [warehouseName, setWarehouseName] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const fetchSettings = useCallback(() => {
    inventoryService.getSettings()
      .then(({ data }) => {
        setSettings({
          inventory_account: data.inventory_account || null,
          cogs_account: data.cogs_account || null,
          adjustments_account: data.adjustments_account || null,
          default_warehouse: data.default_warehouse || null,
        })
        setWarehouseName(data.default_warehouse_name || 'Default warehouse not set')
      })
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
      await inventoryService.updateSettings(settings)
      setSaved(true)
      setWarehouseName(
        (await inventoryService.getSettings()).data.default_warehouse_name ||
        'Default warehouse not set'
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  if (activeTenantRole !== 'Admin') {
    return (
      <div>
        <InventoryNav />
        <div style={pageStyle}>
          <p>Only administrators can configure inventory settings.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <InventoryNav />
      <div style={pageStyle}>
        <h1 style={titleStyle}>Inventory Settings</h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text)', marginBottom: '1.5rem' }}>
          These accounts are used when posting stock receipts, sales (COGS) and
          adjustments. The default warehouse is created automatically and used
          for all posting.
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
              <label style={labelStyle}>Default Warehouse</label>
              <div style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.875rem', background: '#f9f9f9' }}>
                {warehouseName}
              </div>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Inventory Account (Asset)</label>
              <AccountSelect
                value={settings.inventory_account}
                onChange={setField('inventory_account')}
                placeholder="Select Asset account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Cost of Goods Sold (Expense)</label>
              <AccountSelect
                value={settings.cogs_account}
                onChange={setField('cogs_account')}
                placeholder="Select Expense account..."
              />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Stock Adjustments (Expense)</label>
              <AccountSelect
                value={settings.adjustments_account}
                onChange={setField('adjustments_account')}
                placeholder="Select Expense account..."
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