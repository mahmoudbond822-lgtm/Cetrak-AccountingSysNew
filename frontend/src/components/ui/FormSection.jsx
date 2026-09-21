import { color, font, space } from '../../lib/tokens'

const sectionStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[4],
}

const titleStyle = {
  fontSize: font.size.sectionTitle,
  fontWeight: font.weight.semibold,
  color: color.text.primary,
}

const descriptionStyle = {
  fontSize: font.size.bodySmall,
  color: color.text.muted,
}

const fieldsStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: space[4],
}

/**
 * FormSection — consistent heading + field spacing for auth and modal forms.
 */
export default function FormSection({ title, description, children, style }) {
  return (
    <section style={{ ...sectionStyle, ...style }}>
      {(title || description) && (
        <div>
          {title && <div style={titleStyle}>{title}</div>}
          {description && <div style={descriptionStyle}>{description}</div>}
        </div>
      )}
      <div style={fieldsStyle}>{children}</div>
    </section>
  )
}
