import { useState } from 'react'
import api, { setTokens, setActiveTenant, getAuth } from '../../services/api'

export default function TenantSwitcher() {
  const [open, setOpen] = useState(false)
  const { activeTenantId, activeTenantName, activeTenantRole, accessToken } = getAuth()
  const userEmail = localStorage.getItem('userEmail')
  const stored = localStorage.getItem('tenants')
  const tenants = stored ? JSON.parse(stored) : []

  async function handleSwitch(tenant) {
    if (tenant.id === activeTenantId) {
      setOpen(false)
      return
    }
    try {
      const { data } = await api.post(`/tenants/switch/${tenant.id}/`)
      setTokens(data.access, localStorage.getItem('refreshToken'))
      setActiveTenant(data.tenant.id, data.tenant.name, data.tenant.role)
      window.location.reload()
    } catch {
      // switch failed
    }
    setOpen(false)
  }

  if (tenants.length <= 1) return null

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {userEmail && <span style={{ marginRight: 12, color: '#666', fontSize: '0.85em' }}>{userEmail}</span>}
      <button onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
        {activeTenantName || 'Select Tenant'} ({activeTenantRole}) ▾
      </button>
      {open && (
        <ul
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            margin: 0,
            padding: '4px 0',
            listStyle: 'none',
            background: '#fff',
            border: '1px solid #ccc',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '180px',
          }}
        >
          {tenants.map((t) => (
            <li key={t.id} style={{ borderBottom: '1px solid #eee' }}>
              <button
                onClick={() => handleSwitch(t)}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '8px 12px',
                  textAlign: 'left',
                  border: 'none',
                  background: t.id === activeTenantId ? '#f0f0f0' : 'transparent',
                  cursor: 'pointer',
                  fontWeight: t.id === activeTenantId ? 'bold' : 'normal',
                }}
              >
                {t.name} <span style={{ color: '#666', fontSize: '0.85em' }}>({t.role})</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
