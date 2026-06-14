import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { setActiveTenant } from '../services/api'

export default function TenantSelectPage() {
  const [tenants, setTenants] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    async function fetchTenants() {
      try {
        const { data } = await api.get('/auth/me/')
      } catch {
        navigate('/login', { replace: true })
      }
    }
    fetchTenants()
  }, [navigate])

  // For now, tenants come from the login response
  // Parse them from stored login data or re-fetch
  useEffect(() => {
    const stored = localStorage.getItem('tenants')
    if (stored) {
      setTenants(JSON.parse(stored))
    }
  }, [])

  function handleSelect(tenant) {
    setActiveTenant(tenant.id, tenant.name, tenant.role)
    navigate('/', { replace: true })
  }

  if (tenants.length === 0) {
    return <p>Loading your tenants...</p>
  }

  return (
    <div>
      <h1>Select a Workspace</h1>
      <p>You have access to multiple workspaces. Choose one to continue.</p>
      <ul>
        {tenants.map((t) => (
          <li key={t.id}>
            <button onClick={() => handleSelect(t)}>
              <strong>{t.name}</strong> <span>({t.role})</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
