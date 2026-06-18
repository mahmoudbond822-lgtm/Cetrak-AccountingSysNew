import { useNavigate } from 'react-router-dom'
import api, { getAuth, clearAuth } from '../services/api'
import TenantSwitcher from '../components/Layout/TenantSwitcher'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { activeTenantName, refreshToken } = getAuth()

  async function handleLogout() {
    try {
      await api.post('/auth/logout/', { refresh: refreshToken })
    } catch {
      // proceed even if server call fails
    }
    clearAuth()
    navigate('/login', { replace: true })
  }

  return (
    <div>
      <header style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h1>{activeTenantName || 'Dashboard'}</h1>
        <TenantSwitcher />
        <button onClick={handleLogout}>Logout</button>
      </header>
      <p>Welcome to your dashboard. Your accounting system is ready.</p>
    </div>
  )
}
