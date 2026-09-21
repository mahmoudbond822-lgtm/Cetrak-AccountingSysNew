import { color, font, space } from '../../lib/tokens'
import { Card } from '../ui'

const pageStyle = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: color.bg.app,
  padding: space[4],
}

const layoutStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: space[6],
  width: '100%',
  maxWidth: '416px',
}

const brandStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[3],
  textDecoration: 'none',
}

const logoStyle = {
  width: '40px',
  height: '40px',
  borderRadius: 'var(--radius-md)',
  background: color.brand.primary,
  color: color.brand.foreground,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: '19px',
  letterSpacing: '-0.02em',
}

const wordmarkStyle = {
  fontSize: '20px',
  fontWeight: 700,
  color: color.text.primary,
  letterSpacing: '-0.01em',
}

const taglineStyle = {
  fontSize: font.size.caption,
  color: color.text.muted,
  textAlign: 'center',
}

const cardStyle = {
  width: '100%',
  padding: `${space[6]} ${space[6]}`,
}

const footerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: space[2],
  fontSize: font.size.bodySmall,
  color: color.text.muted,
}

/**
 * AuthLayout — shared centered composition for Login / Register / invitation.
 *
 * Brand lockup, restrained type hierarchy, one card. No marketing filler.
 */
export default function AuthLayout({ children, footer }) {
  return (
    <div style={pageStyle}>
      <div style={layoutStyle}>
        <div style={brandStyle}>
          <span style={logoStyle} aria-hidden="true">C</span>
          <span style={wordmarkStyle}>Cetrak</span>
        </div>
        <p style={taglineStyle}>Professional accounting for modern teams</p>
        <Card style={cardStyle}>{children}</Card>
        {footer && <div style={footerStyle}>{footer}</div>}
      </div>
    </div>
  )
}
