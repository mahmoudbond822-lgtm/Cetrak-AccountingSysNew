import { useState } from 'react'
import api, { setTokens, setActiveTenant, getAuth } from '../../services/api'
import { color, font, space } from '../../lib/tokens'
import { Dropdown } from '../ui'

const switcherButtonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: space[2],
  border: `1px solid ${color.border.default}`,
  background: color.bg.surface,
  borderRadius: 'var(--radius-sm)',
  padding: `${space[1]} ${space[2]}`,
  height: '34px',
  color: color.text.primary,
  fontSize: font.size.bodySmall,
  cursor: 'pointer',
  maxWidth: '220px',
}

const orgIconStyle = {
  width: '22px',
  height: '22px',
  borderRadius: 'var(--radius-sm)',
  background: color.brand.soft,
  color: color.brand.primary,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

const nameStyle = {
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  fontWeight: font.weight.medium,
}

/**
 * TenantSwitcher — organization selector.
 *
 * Behavior preserved exactly: uses the existing `/tenants/switch/{id}/` endpoint,
 * stores the returned tenant, and reloads. Only the presentation changes.
 * Renders nothing when the user belongs to a single tenant (unchanged).
 */
export default function TenantSwitcher() {
  const [busy, setBusy] = useState(false)
  const { activeTenantId, activeTenantName } = getAuth()
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('tenants') : null
  const tenants = stored ? JSON.parse(stored) : []

  if (tenants.length <= 1) return null

  async function handleSwitch(tenant) {
    if (tenant.id === activeTenantId || busy) return
    setBusy(true)
    try {
      const { data } = await api.post(`/tenants/switch/${tenant.id}/`)
      setTokens(data.access)
      setActiveTenant(data.tenant.id, data.tenant.name, data.tenant.role)
      window.location.reload()
    } catch {
      setBusy(false)
    }
  }

  return (
    <Dropdown
      align="left"
      trigger={() => (
        <button
          type="button"
          style={switcherButtonStyle}
          className="cetrak-focus-visible"
          aria-label="Switch organization"
          aria-haspopup="menu"
          disabled={busy}
        >
          <span style={orgIconStyle} aria-hidden="true">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" />
            </svg>
          </span>
          <span style={nameStyle}>{activeTenantName || 'Select organization'}</span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      )}
      items={tenants.map((t) => ({
        label: `${t.name} (${t.role})`,
        onClick: () => handleSwitch(t),
      }))}
    />
  )
}
