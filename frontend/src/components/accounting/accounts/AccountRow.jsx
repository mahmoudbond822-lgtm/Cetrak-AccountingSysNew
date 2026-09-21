import { useState } from 'react'
import { AccountingTypeBadge, Badge, Button } from '../../ui'
import { color, font, space } from '../../../lib/tokens'

const rowStyle = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) 132px 120px 128px',
  alignItems: 'center',
  gap: space[3],
  padding: `${space[3]} ${space[4]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
  fontSize: font.size.bodySmall,
}

const toggleBtn = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '24px',
  height: '24px',
  flexShrink: 0,
  border: `1px solid ${color.border.default}`,
  background: color.bg.surface,
  color: color.text.secondary,
  borderRadius: 'var(--radius-sm)',
  cursor: 'pointer',
  padding: 0,
}

const indent = { width: '24px', flexShrink: 0 }

const nameWrapStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[2],
  minWidth: 0,
}

const nameStyle = {
  fontWeight: font.weight.medium,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}

const actionsStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: space[1],
}

/**
 * AccountRow — one ledger account line in the Chart of Accounts tree.
 *
 * Preserves the existing expand/collapse behavior for child accounts.
 * Type uses the global accounting token map (dot + label, never color alone);
 * actions are visually categorized: Edit is secondary, Deactivate is destructive.
 */
export default function AccountRow({ account, onEdit, onDeactivate, depth = 0 }) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = account.children && account.children.length > 0
  const isActive = account.is_active !== false

  return (
    <>
      <div style={{ ...rowStyle, paddingLeft: `calc(${space[4]} + ${depth * 20}px)` }}>
        <div style={nameWrapStyle}>
          {hasChildren ? (
            <button
              type="button"
              style={toggleBtn}
              className="cetrak-focus-visible"
              onClick={() => setExpanded(!expanded)}
              aria-expanded={expanded}
              aria-label={expanded ? `Collapse ${account.name}` : `Expand ${account.name}`}
              title={expanded ? 'Collapse' : 'Expand'}
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)' }}
                aria-hidden="true"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          ) : (
            <div style={indent} aria-hidden="true" />
          )}
          <span style={nameStyle} title={account.name}>
            {account.name}
          </span>
        </div>

        <AccountingTypeBadge type={account.type} size="sm" />

        <Badge tone={isActive ? 'success' : 'neutral'} size="sm" dot>
          {isActive ? 'Active' : 'Inactive'}
        </Badge>

        <div style={actionsStyle}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(account)}
            aria-label={`Edit ${account.name}`}
          >
            Edit
          </Button>
          {isActive && (
            <Button
              variant="dangerSoft"
              size="sm"
              onClick={() => onDeactivate(account)}
              aria-label={`Deactivate ${account.name}`}
            >
              Deactivate
            </Button>
          )}
        </div>
      </div>
      {expanded && hasChildren && account.children.map((child) => (
        <AccountRow
          key={child.id}
          account={child}
          onEdit={onEdit}
          onDeactivate={onDeactivate}
          depth={depth + 1}
        />
      ))}
    </>
  )
}
