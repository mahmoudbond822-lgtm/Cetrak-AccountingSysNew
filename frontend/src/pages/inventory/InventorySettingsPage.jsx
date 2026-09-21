import { useState, useEffect, useCallback } from 'react'
import AccountSelect from '../../components/accounting/journal/AccountSelect'
import { getAuth } from '../../services/api'
import { inventoryService } from '../../services/inventoryService'
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
      <PageContainer>
        <PageHeader title="Inventory Settings" />
        <Card>
          <CardBody>
            <p style={helperStyle}>Only administrators can configure inventory settings.</p>
          </CardBody>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Inventory Settings"
        description="Default accounts and warehouse used when posting stock movements."
        breadcrumbs={[{ label: 'Inventory' }, { label: 'Settings' }]}
      />

      <p style={helperStyle}>
        These accounts are used when posting stock receipts, sales (COGS) and
        adjustments. The default warehouse is created automatically and used
        for all posting.
      </p>

      {error && (
        <Alert tone="error" dismissible onDismiss={setError} style={{ marginBottom: space[4] }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardBody>
            <Skeleton count={4} height="38px" />
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardBody>
            <div style={fieldStyle}>
              <label style={labelStyle}>Default Warehouse</label>
              <div style={{
                padding: `${space[2]} ${space[3]}`,
                border: '1px solid var(--border)',
                borderRadius: '6px',
                fontSize: font.size.bodySmall,
                background: 'var(--bg-hover)',
              }}>
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
            <div style={{ display: 'flex', gap: space[3], alignItems: 'center' }}>
              <Button variant="primary" onClick={handleSave} loading={saving}>
                {saving ? 'Saving…' : 'Save Settings'}
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
