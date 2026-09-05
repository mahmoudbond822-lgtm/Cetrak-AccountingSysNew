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

export default function InventoryNav() {
  const { activeTenantRole } = getAuth()
  const isAdmin = activeTenantRole === 'Admin'

  return (
    <nav style={navStyle}>
      <NavLink to="/inventory/products" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
        Products
      </NavLink>
      <NavLink to="/inventory/stock" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
        Stock
      </NavLink>
      <NavLink to="/inventory/adjustments" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
        Adjustments
      </NavLink>
      {isAdmin && (
        <NavLink to="/inventory/settings" style={({ isActive }) => isActive ? activeStyle : linkStyle}>
          Settings
        </NavLink>
      )}
    </nav>
  )
}