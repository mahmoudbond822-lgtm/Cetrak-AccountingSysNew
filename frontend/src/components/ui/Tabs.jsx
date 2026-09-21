import { useId } from 'react'
import { color, font, space } from '../../lib/tokens'
import { cn } from '../../lib/cn'

const listStyle = {
  display: 'flex',
  gap: space[1],
  borderBottom: `1px solid ${color.border.default}`,
}

const tabStyle = {
  border: 'none',
  background: 'transparent',
  padding: `${space[3]} ${space[4]}`,
  fontSize: font.size.bodySmall,
  fontWeight: font.weight.medium,
  color: color.text.muted,
  cursor: 'pointer',
  position: 'relative',
  whiteSpace: 'nowrap',
}

const tabActiveStyle = {
  color: color.brand.primary,
  fontWeight: font.weight.semibold,
}

const tabIndicatorStyle = {
  position: 'absolute',
  left: space[3],
  right: space[3],
  bottom: '-1px',
  height: '2px',
  background: color.brand.primary,
  borderRadius: '2px 2px 0 0',
}

/**
 * Tabs — controlled tablist.
 *
 * Available for detail pages; adopted only where a real tab UI is needed.
 */
export default function Tabs({ tabs, value, onChange, className, style }) {
  const groupId = useId()

  return (
    <div className={cn(className)} style={{ ...listStyle, ...style }} role="tablist">
      {tabs.map((tab) => {
        const active = tab.value === value
        return (
          <button
            key={tab.value}
            id={`${groupId}-${tab.value}`}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls={`${groupId}-${tab.value}-panel`}
            style={{ ...tabStyle, ...(active ? tabActiveStyle : null) }}
            className="cetrak-focus-visible"
            onClick={() => onChange(tab.value)}
          >
            {tab.label}
            {active && <span style={tabIndicatorStyle} aria-hidden="true" />}
          </button>
        )
      })}
    </div>
  )
}

export function TabPanel({ value, tabValue, children, className, style }) {
  const groupId = useId()
  if (value !== tabValue) return null
  return (
    <div
      className={cn(className)}
      role="tabpanel"
      id={`${groupId}-${tabValue}-panel`}
      style={{ padding: `${space[5]} 0`, ...style }}
    >
      {children}
    </div>
  )
}
