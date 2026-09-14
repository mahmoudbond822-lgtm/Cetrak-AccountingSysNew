import { NavLink, Link, Outlet, useNavigate } from 'react-router-dom'
import api, { getAuth, clearAuth, csrfToken } from '../../services/api'
import TenantSwitcher from './TenantSwitcher'

const navItemStyle = {
  display: 'block',
  padding: '0.5rem 1rem',
  textDecoration: 'none',
  color: 'var(--text)',
  borderRadius: '6px',
  fontSize: '0.875rem',
}

const activeNavItemStyle = {
  ...navItemStyle,
  background: 'var(--accent)',
  color: '#fff',
}

const groupLabelStyle = {
  padding: '0.75rem 1rem 0.25rem',
  fontSize: '0.7rem',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-muted, #888)',
}

export default function AppLayout() {
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
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          width: '220px',
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          background: 'var(--bg)',
          padding: '1rem 0.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
        }}
      >
        <div style={{ padding: '0 1rem 0.75rem', fontWeight: 600, color: 'var(--text)' }}>
          {activeTenantName || 'Cetrak'}
        </div>
        <TenantSwitcher />

        <div style={groupLabelStyle}>Accounting</div>
        <NavLink to="/accounting/accounts" end style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Accounts
        </NavLink>
        <NavLink to="/accounting/journal" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Journal
        </NavLink>
        <NavLink to="/accounting/reports" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Reports
        </NavLink>

        <div style={groupLabelStyle}>Sales</div>
        <NavLink to="/sales/customers" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Customers
        </NavLink>
        <NavLink to="/sales/invoices" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Invoices
        </NavLink>
        <NavLink to="/sales/payments" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Payments
        </NavLink>

        <div style={groupLabelStyle}>Purchases</div>
        <NavLink to="/purchases/vendors" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Vendors
        </NavLink>
        <NavLink to="/purchases/invoices" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Purchase Invoices
        </NavLink>
        <NavLink to="/purchases/payments" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Payments
        </NavLink>

        <div style={groupLabelStyle}>Inventory</div>
        <NavLink to="/inventory/products" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Products
        </NavLink>
        <NavLink to="/inventory/stock" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Stock
        </NavLink>
        <NavLink to="/inventory/adjustments" style={({ isActive }) => (isActive ? activeNavItemStyle : navItemStyle)}>
          Adjustments
        </NavLink>

        <div style={{ flex: 1 }} />

        <Link to="/team" style={navItemStyle}>
          Team
        </Link>
        <button
          onClick={handleLogout}
          style={{
            margin: '0.5rem 1rem',
            padding: '0.5rem 1rem',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            background: 'transparent',
            color: 'var(--text)',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          Logout
        </button>
      </aside>
      <main style={{ flex: 1, minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  )
}
