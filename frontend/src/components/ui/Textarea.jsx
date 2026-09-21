import { cn } from '../../lib/cn'
import FormField from './FormField'

/**
 * Textarea — multi-line text control with the Input contract.
 */
export default function Textarea({
  label,
  helperText,
  error,
  required,
  disabled,
  className,
  style,
  id,
  rows = 4,
  ...props
}) {
  const control = (a11y) => (
    <textarea
      id={id || a11y.id}
      rows={rows}
      className={cn('cetrak-input', className)}
      style={style}
      disabled={disabled}
      required={required}
      {...a11y}
      {...props}
    />
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
