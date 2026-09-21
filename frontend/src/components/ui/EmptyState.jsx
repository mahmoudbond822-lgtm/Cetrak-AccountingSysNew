import { color, font, space } from '../../lib/tokens'
import Card from './Card'

const containerStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
  gap: space[3],
  padding: `${space[10]} ${space[6]}`,
}

const iconWrapperStyle = {
  width: '48px',
  height: '48px',
  borderRadius: 'var(--radius-pill)',
  background: color.bg.hover,
  color: color.text.muted,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

const titleStyle = {
  fontSize: font.size.sectionTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
}

const descriptionStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.muted,
  maxWidth: '420px',
}

const actionStyle = {
  display: 'flex',
  gap: space[2],
  marginTop: space[1],
}

function DefaultIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M9 9v11" />
    </svg>
  )
}

/**
 * EmptyState — standardized "no data" presentation.
 *
 * Used by every data view so that "no accounts / invoices / customers /
 * transactions" never results in a blank screen.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  inCard = false,
  style,
}) {
  const content = (
    <div style={{ ...containerStyle, ...style }} role="status">
      <div style={iconWrapperStyle}>{icon || <DefaultIcon />}</div>
      <div style={titleStyle}>{title}</div>
      {description && <div style={descriptionStyle}>{description}</div>}
      {(action || secondaryAction) && (
        <div style={actionStyle}>
          {secondaryAction}
          {action}
        </div>
      )}
    </div>
  )

  return inCard ? <Card>{content}</Card> : content
}
