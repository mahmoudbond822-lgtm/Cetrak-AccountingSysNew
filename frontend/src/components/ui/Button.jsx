import { cn } from '../../lib/cn'

const baseClass = 'cetrak-button cetrak-focus-visible'

const variantClass = {
  primary: 'cetrak-button-primary',
  secondary: 'cetrak-button-secondary',
  outline: 'cetrak-button-outline',
  ghost: 'cetrak-button-ghost',
  danger: 'cetrak-button-danger',
  dangerSoft: 'cetrak-button-danger-soft',
  link: 'cetrak-button-link',
}

/**
 * Cetrak Button.
 *
 * Variants: primary (brand), secondary (surface), outline (brand outline),
 * ghost (transparent), danger / dangerSoft (destructive — deliberately distinct),
 * link. States: hover/active/disabled via CSS classes, `loading` shows a spinner.
 *
 * Render as a link by passing `as="a"` or `as={Link}` with `to`.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  type = 'button',
  className,
  children,
  as: Component = 'button',
  ...props
}) {
  const classes = cn(
    baseClass,
    variantClass[variant] || variantClass.primary,
    size === 'sm' && 'cetrak-button-sm',
    className,
  )

  const isDisabled = disabled || loading

  return (
    <Component
      className={classes}
      type={Component === 'button' ? type : undefined}
      disabled={Component === 'button' ? isDisabled : undefined}
      aria-disabled={isDisabled || undefined}
      {...props}
    >
      {loading && <span className="cetrak-button-spinner" aria-hidden="true" />}
      {children}
    </Component>
  )
}
