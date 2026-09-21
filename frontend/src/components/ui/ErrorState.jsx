import { color, font, space } from '../../lib/tokens'
import Button from './Button'

const containerStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
  gap: space[3],
  padding: `${space[3]} ${space[6]}`,
}

const iconWrapperStyle = {
  width: '48px',
  height: '48px',
  borderRadius: 'var(--radius-pill)',
  background: color.semantic.dangerSoft,
  color: color.semantic.danger,
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

function WarningIcon() {
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
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  )
}

/**
 * ErrorState — standardized failed-load presentation with an optional retry action.
 */
export default function ErrorState({
  title = 'Something went wrong',
  description = 'We could not load this data. Please try again.',
  retryLabel = 'Try again',
  onRetry,
  style,
}) {
  return (
    <div style={{ ...containerStyle, ...style }} role="alert">
      <div style={iconWrapperStyle}>
        <WarningIcon />
      </div>
      <div style={titleStyle}>{title}</div>
      <div style={descriptionStyle}>{description}</div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
