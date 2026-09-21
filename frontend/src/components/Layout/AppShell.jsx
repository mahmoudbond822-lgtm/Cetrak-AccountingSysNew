import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { color } from '../../lib/tokens'
import { Drawer } from '../ui'
import { LG_BREAKPOINT, useMediaQuery } from '../../lib/hooks'
import { getAuth } from '../../services/api'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import TenantSwitcher from './TenantSwitcher'

const shellStyle = {
  display: 'flex',
  minHeight: '100vh',
  background: color.bg.app,
}

const mainColumnStyle = {
  flex: 1,
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
}

const mainStyle = {
  flex: 1,
  minWidth: 0,
}

/**
 * AppShell — the application frame.
 *
 * Desktop (>= 1024px): persistent Sidebar with a collapse toggle.
 * Tablet/mobile (< 1024px): Sidebar moves into a Drawer opened from the TopBar;
 * the drawer closes automatically on route change.
 *
 * Navigation destinations and role guards are unchanged (see src/lib/nav.js).
 */
export default function AppShell() {
  const isDesktop = useMediaQuery(LG_BREAKPOINT)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { activeTenantRole } = getAuth()

  return (
    <div style={shellStyle}>
      {isDesktop && (
        <Sidebar
          collapsed={collapsed}
          role={activeTenantRole}
          onToggleCollapse={() => setCollapsed((v) => !v)}
        />
      )}

      <div style={mainColumnStyle}>
        <TopBar
          onOpenNavigation={() => setMobileNavOpen(true)}
          tenantSwitcher={<TenantSwitcher />}
        />
        <main style={mainStyle} id="cetrak-main">
          <Outlet />
        </main>
      </div>

      {!isDesktop && (
        <Drawer
          open={mobileNavOpen}
          onClose={() => setMobileNavOpen(false)}
          side="left"
          aria-label="Navigation"
        >
          <Sidebar
            role={activeTenantRole}
            onNavigate={() => setMobileNavOpen(false)}
          />
        </Drawer>
      )}
    </div>
  )
}
