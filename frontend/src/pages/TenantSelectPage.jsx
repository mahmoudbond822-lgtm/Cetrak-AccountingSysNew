import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { setActiveTenant } from '../services/api'
import AuthLayout from '../components/layout/AuthLayout'
import { Button, Card, CardBody, Skeleton } from '../components/ui'
import { color, font, space } from '../lib/tokens'

const listStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[2],
}

const tenantButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[3],
  width: '100%',
  textAlign: 'left',
  padding: `${space[3]} ${space[4]}`,
  border: `1px solid ${color.border.default}`,
  background: color.bg.surface,
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
  color: color.text.primary,
  fontSize: font.size.bodySmall,
}

const orgIconStyle = {
  width: '32px',
  height: '32px',
  borderRadius: 'var(--radius-sm)',
  background: color.brand.soft,
  color: color.brand.primary,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  fontWeight: 600,
}

const titleStyle = {
  fontSize: font.size.pageTitle,
  fontWeight: 600,
  color: color.text.primary,
  textAlign: 'center',
}

const subtitleStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.muted,
  textAlign: 'center',
}

export default function TenantSelectPage() {
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function fetchTenants() {
      try {
        await api.get('/auth/me/')
      } catch {
        navigate('/login', { replace: true })
      }
    }
    fetchTenants()
  }, [navigate])

  useEffect(() => {
    const stored = localStorage.getItem('tenants')
    if (stored) {
      setTenants(JSON.parse(stored))
    }
    setLoading(false)
  }, [])

  function handleSelect(tenant) {
    setActiveTenant(tenant.id, tenant.name, tenant.role)
    navigate('/', { replace: true })
  }

  return (
    <AuthLayout>
      <h1 style={titleStyle}>Select a workspace</h1>
      <p style={subtitleStyle}>
        You have access to multiple workspaces. Choose one to continue.
      </p>

      {loading ? (
        <Skeleton count={3} height="56px" />
      ) : tenants.length === 0 ? (
        <Card>
          <CardBody>
            <p style={{ fontSize: font.size.bodySmall, color: color.text.muted }}>
              Loading your workspaces…
            </p>
          </CardBody>
        </Card>
      ) : (
        <div style={listStyle}>
          {tenants.map((t) => (
            <button
              key={t.id}
              type="button"
              style={tenantButtonStyle}
              className="cetrak-focus-visible"
              onClick={() => handleSelect(t)}
            >
              <span style={orgIconStyle} aria-hidden="true">
                {t.name?.charAt(0)?.toUpperCase() || '?'}
              </span>
              <span style={{ minWidth: 0 }}>
                <span style={{ display: 'block', fontWeight: font.weight.semibold }}>
                  {t.name}
                </span>
                <span style={{ fontSize: font.size.caption, color: color.text.muted }}>
                  {t.role}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}

      <Button variant="link" onClick={() => { localStorage.clear(); navigate('/login') }}>
        Sign out
      </Button>
    </AuthLayout>
  )
}
