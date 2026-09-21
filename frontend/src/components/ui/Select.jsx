import { cn } from '../../lib/cn'
import FormField from './FormField'

/**
 * Select — styled native select.
 *
 * Native element on purpose: keyboard navigation, screen-reader support and
 * mobile pickers come for free. Styled to match Input; chevron via CSS.
 * Same label/helper/error contract as Input.
 */
export default function Select({
  label,
  helperText,
  error,
  required,
  disabled,
  className,
  style,
  id,
  children,
  ...props
}) {
  const control = (a11y) => (
    <select
      id={id || a11y.id}
      className={cn('cetrak-select', className)}
      style={style}
      disabled={disabled}
      required={required}
      {...a11y}
      {...props}
    >
      {children}
    </select>
  )

  if (label || helperText || error) {
    return (
      <FormField label={label} helperText={helperText} error={error} required={required}>
        {control}
      </FormField>
    )
  }
  return control({ id, 'aria-invalid': error ? 'true' : undefined })
}
