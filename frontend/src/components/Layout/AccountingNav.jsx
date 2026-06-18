import { NavLink } from 'react-router-dom'
import { getAuth } from '../../services/api'

const linkStyle = {
  padding: '0.5rem 1rem',
  textDecoration: 'none',
  color: 'var(--text)',
  borderRadius: '6px',
  fontSize: '0.875rem',
}

const activeStyle = {
  ...linkStyle,
  background: 'var(--accent)',
  color: '#fff',
}

const navStyle = {
  display: 'flex',
  gap: '0.25rem',
  padding: '0.75rem 1.5rem',
  borderBottom: '1px solid var(--border)',
  background: 'var(--bg)',
  flexWrap: 'wrap',
}

export default function AccountingNav() {
  const { activeTenantRole } = getAuth()
  const isManager = activeTenantRole === 'Manager'

  return (
    <nav style={navStyle}>
      <NavLink to="/accounting/accounts" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
        Chart of Accounts
      </NavLink>
      <NavLink to="/accounting/journal" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
        Journal Entries
      </NavLink>
      {!isManager && (
        <NavLink to="/accounting/reports" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
          Reports
        </NavLink>
      )}
    </nav>
  )
}
