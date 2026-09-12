import { useNavigate } from 'react-router-dom'
import api, { getAuth, clearAuth, csrfToken } from '../services/api'
import TenantSwitcher from '../components/Layout/TenantSwitcher'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { activeTenantName } = getAuth()

  async function handleLogout() {
    try {
      const csrf = csrfToken()
      const config = csrf
        ? { withCredentials: true, headers: { 'X-CSRFToken': csrf } }
        : { withCredentials: true }
      await api.post('/auth/logout/', {}, config)
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