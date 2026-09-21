import api, { getAuth, clearAuth, csrfToken } from '../../services/api'
import { color, font, space } from '../../lib/tokens'
import { Dropdown } from '../ui'

const barStyle = {
  position: 'sticky',
  top: 0,
  zIndex: 'var(--z-sticky)',
  height: 'var(--topbar-height)',
  display: 'flex',
  alignItems: 'center',
  gap: space[3],
  padding: `0 ${space[5]}`,
  background: color.bg.surface,
  borderBottom: `1px solid ${color.border.default}`,
}

const menuButtonStyle = {
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
}

const userInfoStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-start',
  lineHeight: 1.2,
  minWidth: 0,
}

const emailStyle = {
  fontSize: font.size.bodySmall,
  fontWeight: font.weight.medium,
  color: color.text.primary,
  maxWidth: '180px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}

const roleStyle = {
  fontSize: '11px',
  color: color.text.muted,
}

const avatarStyle = {
  width: '28px',
  height: '28px',
  borderRadius: '50%',
  background: color.brand.soft,
  color: color.brand.primary,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '12px',
  fontWeight: 700,
  flexShrink: 0,
}

const iconButtonStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '34px',
  height: '34px',
  border: `1px solid ${color.border.default}`,
  background: color.bg.surface,
  borderRadius: 'var(--radius-sm)',
  color: color.text.secondary,
  cursor: 'pointer',
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}

function initials(email) {
  if (!email) return '?'
  return email.charAt(0).toUpperCase()
}

/**
 * TopBar — sticky global bar.
 *
 * Mobile: hamburger opens the navigation drawer. Desktop: tenant switcher +
 * user menu with logout. No fake features.
 */
export default function TopBar({ onOpenNavigation, tenantSwitcher }) {
  const { activeTenantRole, activeTenantName } = getAuth()
  const userEmail = typeof localStorage !== 'undefined' ? localStorage.getItem('userEmail') : null

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
    window.location.href = '/login'
  }

  return (
    <header style={barStyle}>
      <button
        type="button"
        style={iconButtonStyle}
        onClick={onOpenNavigation}
        aria-label="Open navigation"
        className="cetrak-focus-visible cetrak-lg-hidden"
      >
        <MenuIcon />
      </button>

      {tenantSwitcher}

      <div style={{ flex: 1 }} />

      <Dropdown
        align="right"
        trigger={() => (
          <button
            type="button"
            style={menuButtonStyle}
            className="cetrak-focus-visible"
            aria-label="User menu"
          >
            <span style={avatarStyle} aria-hidden="true">{initials(userEmail)}</span>
            <span style={userInfoStyle}>
              <span style={emailStyle}>{userEmail || activeTenantName || 'Account'}</span>
              <span style={roleStyle}>{activeTenantRole || ''}</span>
            </span>
            <ChevronDownIcon />
          </button>
        )}
        items={[
          {
            label: 'Sign out',
            icon: <LogoutIcon />,
            onClick: handleLogout,
            tone: 'danger',
          },
        ]}
      />
    </header>
  )
}
