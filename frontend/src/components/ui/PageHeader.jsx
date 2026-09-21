import { color, font, space, layout } from '../../lib/tokens'
import { cn } from '../../lib/cn'

const containerStyle = {
  width: '100%',
  maxWidth: layout.contentWidth,
  margin: '0 auto',
  padding: `${space[6]} ${space[6]}`,
}

const headerStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: space[4],
  flexWrap: 'wrap',
  marginBottom: space[5],
}

const titleBlockStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[1],
  minWidth: 0,
}

const titleStyle = {
  fontSize: font.size.pageTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
  lineHeight: font.leading.snug,
}

const descriptionStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.muted,
}

const breadcrumbStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[1],
  fontSize: font.size.caption,
  color: color.text.muted,
  marginBottom: space[1],
}

const actionsStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: space[2],
  flexWrap: 'wrap',
}

/**
 * PageContainer — standard content width + responsive padding for every page.
 * Replaces the per-page 720/960/1024px inconsistency with one `--content-width`.
 */
export function PageContainer({ className, style, children }) {
  return (
    <div className={cn(className)} style={{ ...containerStyle, ...style }}>
      {children}
    </div>
  )
}

/**
 * PageHeader — standard page top: title, description, breadcrumbs, actions.
 *
 * `primaryAction` renders on the right (primary), `secondaryActions` beside it.
 */
export function PageHeader({
  title,
  description,
  breadcrumbs,
  primaryAction,
  secondaryActions,
  className,
  style,
}) {
  return (
    <div className={cn(className)} style={{ ...headerStyle, ...style }}>
      <div style={titleBlockStyle}>
        {breadcrumbs?.length > 0 && (
          <nav style={breadcrumbStyle} aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: space[1] }}>
                {i > 0 && (
                  <span aria-hidden="true" style={{ opacity: 0.6 }}>
                    /
                  </span>
                )}
                {crumb.href ? (
                  <a
                    href={crumb.href}
                    style={{
                      color: color.text.muted,
                      textDecoration: 'none',
                    }}
                  >
                    {crumb.label}
                  </a>
                ) : (
                  <span>{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <h1 style={titleStyle}>{title}</h1>
        {description && <p style={descriptionStyle}>{description}</p>}
      </div>
      {(primaryAction || secondaryActions) && (
        <div style={actionsStyle}>
          {secondaryActions}
          {primaryAction}
        </div>
      )}
    </div>
  )
}

export default PageHeader
