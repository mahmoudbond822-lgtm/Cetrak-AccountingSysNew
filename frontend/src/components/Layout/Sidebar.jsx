import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { color, font, space } from '../../lib/tokens'
import { dashboardNavItem, filterByRole, navGroups } from '../../lib/nav'

const asideStyle = (collapsed) => ({
  width: collapsed ? 'var(--sidebar-width-collapsed)' : 'var(--sidebar-width)',
  flexShrink: 0,
  background: color.bg.surface,
  borderRight: `1px solid ${color.border.default}`,
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflowY: 'auto',
  transition: 'width 160ms ease',
})

const brandStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[3],
  padding: `${space[4]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
}

const logoStyle = {
  width: '32px',
  height: '32px',
  borderRadius: 'var(--radius-md)',
  background: color.brand.primary,
  color: color.brand.foreground,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  fontWeight: 700,
  fontSize: '15px',
  letterSpacing: '-0.02em',
}

const wordmarkStyle = {
  fontSize: font.size.cardTitle,
  fontWeight: 700,
  color: color.text.primary,
  letterSpacing: '-0.01em',
  whiteSpace: 'nowrap',
}

const groupLabelStyle = {
  padding: `${space[3]} ${space[4]} ${space[1]}`,
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: color.text.muted,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
}

const moduleButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: space[2],
  width: '100%',
  padding: `0 ${space[3]}`,
  height: '34px',
  margin: '1px 0',
  borderRadius: 'var(--radius-sm)',
  border: 'none',
  background: 'transparent',
  color: color.text.primary,
  fontSize: font.size.bodySmall,
  fontWeight: font.weight.semibold,
  cursor: 'pointer',
  textAlign: 'left',
}

const childListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '1px',
  padding: `0 ${space[2]}`,
}

const childLinkStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[2],
  padding: `0 ${space[2]}`,
  height: '30px',
  borderRadius: 'var(--radius-sm)',
  color: color.text.secondary,
  textDecoration: 'none',
  fontSize: font.size.bodySmall,
  fontWeight: font.weight.regular,
}

const spacerStyle = { flex: 1 }

const collapseButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[2],
  margin: `${space[2]} ${space[2]}`,
  padding: `0 ${space[3]}`,
  height: '32px',
  border: 'none',
  background: 'transparent',
  color: color.text.muted,
  borderRadius: 'var(--radius-sm)',
  fontSize: font.size.caption,
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
}

function CollapseIcon({ collapsed }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)' }}
      aria-hidden="true"
    />
  )
}

function ChevronIcon({ open }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        flexShrink: 0,
        transition: 'transform 160ms ease',
        transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
      }}
      aria-hidden="true"
    />
  )
}

function ModuleItem({ item, role, onNavigate }) {
  const [open, setOpen] = useState(true)
  const children = filterByRole(item.children || [], role)

  return (
    <div>
      <button
        type="button"
        className="cetrak-focus-visible"
        style={moduleButtonStyle}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>{item.label}</span>
        <ChevronIcon open={open} />
      </button>
      {open && (
        <div style={childListStyle}>
          {children.map((child) => (
            <NavLink
              key={child.to}
              to={child.to}
              onClick={onNavigate}
              className="cetrak-nav-link cetrak-focus-visible"
              style={childLinkStyle}
            >
              {child.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

function ModuleGroup({ group, role, collapsed, onNavigate }) {
  const [open, setOpen] = useState(true)
  const items = filterByRole(group.items || [], role)

  if (items.length === 0) return null

  if (collapsed) {
    return (
      <>
        <div style={groupLabelStyle}>{group.label[0]}</div>
        {items.map((item) => (
          <NavLink
            key={item.id || item.to}
            to={item.to || item.children?.[0]?.to}
            onClick={onNavigate}
            title={item.label}
            aria-label={item.label}
            className="cetrak-nav-link cetrak-focus-visible"
            style={{ justifyContent: 'center', padding: 0 }}
          >
            {item.label[0]}
          </NavLink>
        ))}
      </>
    )
  }

  return (
    <div>
      <div style={{ padding: `0 ${space[2]}` }}>
        <button
          type="button"
          className="cetrak-focus-visible"
          style={moduleButtonStyle}
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <span>{group.label}</span>
          <ChevronIcon open={open} />
        </button>
      </div>
      {open && (
        <div style={childListStyle}>
          {items.map((item) =>
            item.children?.length ? (
              <ModuleItem
                key={item.id || item.to}
                item={item}
                role={role}
                onNavigate={onNavigate}
              />
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onNavigate}
                className="cetrak-nav-link cetrak-focus-visible"
                style={childLinkStyle}
              >
                {item.label}
              </NavLink>
            )
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Sidebar — scalable grouped navigation.
 *
 * Desktop: persistent, collapsible to an icon rail via `collapsed`.
 * Mobile: rendered inside a Drawer by AppShell (`onNavigate` closes it).
 * Active state via `.cetrak-nav-link[aria-current="page"]`.
 */
export default function Sidebar({ collapsed = false, role, onNavigate, onToggleCollapse }) {
  return (
    <aside
      className="cetrak-scroll"
      style={asideStyle(collapsed)}
      aria-label="Main navigation"
    >
      <div style={brandStyle}>
        <span style={logoStyle} aria-hidden="true">C</span>
        {!collapsed && <span style={wordmarkStyle}>Cetrak</span>}
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: space[2], padding: `${space[3]} 0` }}>
        <div style={{ padding: `0 ${space[2]}` }}>
          <NavLink
            to={dashboardNavItem.to}
            onClick={onNavigate}
            end
            className="cetrak-nav-link cetrak-focus-visible"
            style={collapsed ? { justifyContent: 'center', padding: 0 } : undefined}
            title={collapsed ? dashboardNavItem.label : undefined}
            aria-label={collapsed ? dashboardNavItem.label : undefined}
          >
            {collapsed ? dashboardNavItem.label[0] : dashboardNavItem.label}
          </NavLink>
        </div>

        {navGroups.map((group) => (
          <ModuleGroup
            key={group.id}
            group={group}
            role={role}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}
      </nav>

      <div style={spacerStyle} />

      {onToggleCollapse && (
        <button
          type="button"
          className="cetrak-focus-visible"
          style={collapseButtonStyle}
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          <CollapseIcon collapsed={collapsed} />
          {!collapsed && <span>Collapse</span>}
        </button>
      )}
    </aside>
  )
}
