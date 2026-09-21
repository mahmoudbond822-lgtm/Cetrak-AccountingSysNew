import { cn } from '../../lib/cn'
import { color, font, radius, shadow, space } from '../../lib/tokens'

const cardStyle = {
  background: color.bg.surface,
  border: `1px solid ${color.border.default}`,
  borderRadius: radius.md,
  boxShadow: shadow.xs,
}

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: space[3],
  padding: `${space[4]} ${space[5]}`,
  borderBottom: `1px solid ${color.border.subtle}`,
}

const titleStyle = {
  fontSize: font.size.cardTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
}

const bodyStyle = {
  padding: space[5],
}

const footerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[3],
  padding: `${space[4]} ${space[5]}`,
  borderTop: `1px solid ${color.border.subtle}`,
}

export function Card({ className, style, children, ...props }) {
  return (
    <div className={cn('cetrak-card', className)} style={{ ...cardStyle, ...style }} {...props}>
      {children}
    </div>
  )
}

export function CardHeader({ title, actions, className, style, children }) {
  return (
    <div className={className} style={{ ...headerStyle, ...style }}>
      {children ?? (
        <>
          <span style={titleStyle}>{title}</span>
          {actions && <span>{actions}</span>}
        </>
      )}
    </div>
  )
}

export function CardBody({ className, style, children }) {
  return (
    <div className={className} style={{ ...bodyStyle, ...style }}>
      {children}
    </div>
  )
}

export function CardFooter({ className, style, children }) {
  return (
    <div className={className} style={{ ...footerStyle, ...style }}>
      {children}
    </div>
  )
}

export default Card
